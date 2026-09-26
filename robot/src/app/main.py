from __future__ import annotations

import asyncio
import itertools
import logging
import signal
import time
from dataclasses import dataclass

from comm_protocols.messages import (
    CloseCmd,
    DistanceTelemetry,
    MotionTelemetry,
    OpenCmd,
    ResetOriginCmd,
    SettingsCmd,
    SocketWatchCmd,
    StartCmd,
    StopCmd,
)
from comm_protocols.settings import RobotSettings

from app.buttons import Button
from app.buzzer import Buzzer, Sound
from app.ropesocket import RopeSocket
from app.runtime import Runtime
from camera.camera import CameraPair, encode
from display.screen import Status, StatusScreen
from link.client import RobotLink
from link.outbox import Outbox
from link.video import VideoLink
from motion.controller import MotionController
from motion.drive import Drive
from motion.turret import Turret
from tof.vl53l0x import VL53L0X
from vision.detector import DetectorProcess
from vision.pacing import measure_cycle
from vision.report import vision_telemetry

log = logging.getLogger("cableguard")

# How the robot is wired. Everything else the robot runs on is a setting the operator owns
# from the webapp, see comm_protocols/settings.py: this is what a screwdriver changes, not
# a browser, and the software cannot tell whether a pin was rewired anyway

# the stepper that moves the robot along the rope
DRIVE_PUL_PIN = 18
DRIVE_DIR_PIN = 23

# the stepper that swings both cameras around the rope
TURRET_PUL_PIN = 12
TURRET_DIR_PIN = 16

# the two buttons on the robot, each wired from its pin to ground. Both pins are pulled up
# by the pi at boot, so a button held before the software claims it cannot start anything
START_BUTTON_PIN = 5        # red
STOP_BUTTON_PIN  = 6        # white

# the buzzer, wired from its pin to ground. It sits away from the two stepper pulse pins so
# that its own switching has nothing fast to couple into
BUZZER_PIN = 26

# distance sensor, a TOF200C (VL53L0X) on I2C bus 1 (SDA GPIO2, SCL GPIO3)
TOF_I2C_BUS = 1

# status display, a 0.96" 128x64 SSD1306 OLED. It shares I2C bus 1 with the distance sensor
DISPLAY_I2C_BUS = 1
DISPLAY_ADDRESS = 0x3C      # 0x3D on boards where the address pad is bridged
DISPLAY_FLIP = False        # True if the panel is mounted upside down

# the frame a defect was found in travels as a JPEG, the live stream at a lower quality
STREAM_JPEG_QUALITY = 95


# creates function that turns messages into roboter commands
def make_command_handler(rt: Runtime, motion: MotionController, buzzer: Buzzer):
    def handle(cmd):
        if isinstance(cmd, StopCmd):
            log.info("stop requested")
            buzzer.play(Sound.STOP)
            motion.emergency_stop()

        elif isinstance(cmd, StartCmd):
            # The speed is not ours to choose, the scan plan fixed it so that the detector
            # sees every bit of rope once. The round trip through metres is not bit exact,
            # and ramp_to reads anything below start_speed as a stop, so a plan sitting on
            # the drive's lower limit must not fall through it
            scan_speed = max(motion.drive.to_microsteps(rt.plan.speed_mps), motion.drive.start_speed)
            target = scan_speed if cmd.direction == "forward" else -scan_speed
            log.info("start requested: %s at %.3f m/s (%.0f microsteps/s)",
                     cmd.direction, rt.plan.speed_mps, scan_speed)
            buzzer.play(Sound.START)
            motion.request("speed", target)

        elif isinstance(cmd, ResetOriginCmd):
            if motion.drive.moving:
                log.warning("origin reset while moving, the run starts from here anyway")
            log.info("origin reset at %.2f m", motion.drive.metres_done)
            motion.drive.reset_steps_done()
            # the clear distance is measured from a position that just became zero
            rt.rope_socket.rebase(motion.drive.metres_done)

        elif isinstance(cmd, OpenCmd):
            rt.rope_socket.open_by_user()

        elif isinstance(cmd, CloseCmd):
            rt.rope_socket.close_by_user()

        elif isinstance(cmd, SocketWatchCmd):
            rt.rope_socket.set_watch(cmd.enabled)

        elif isinstance(cmd, SettingsCmd):
            # queued here, put in force by the detection cycle once the robot rests
            rt.accept(cmd.version, cmd.settings)

    return handle

# The buttons stand for the two commands the webapp sends most, so they are handed the same
# messages and run through the handler above: whatever a start comes to mean, the button
# follows. lgpio reports the press on its own thread, the command runs on the event loop
def make_button_press(loop, handle):
    def press(cmd):
        log.info("%s button pressed", cmd.type)
        loop.call_soon_threadsafe(handle, cmd)

    return press

# capture frames (streaming res.), encode, hand them to the video link
async def frame_producer(rt: Runtime, video: VideoLink):
    loop = asyncio.get_running_loop()

    while True:
        deadline = loop.time() + 1.0 / rt.settings.stream_fps
        try:
            for idx, lores in await asyncio.to_thread(rt.cams.capture_lores):
                video.submit(idx, encode(lores, STREAM_JPEG_QUALITY))
        except Exception:
            log.exception("capture failed")
        await asyncio.sleep(max(0.0, deadline - loop.time()))

# how the detector is keeping up, for the status display
@dataclass
class DetectionStats:
    cycle_ms: float | None = None     # how long the last detector cycle took

# Turn the cameras and report if the ring does not make it. A jammed ring costs the two
# sides it was meant to show, not the run, so the scan carries on either way
async def turn_cameras(turret: Turret, degrees: float, seconds: float | None = None) -> bool:
    try:
        await asyncio.to_thread(turret.turn_to, degrees, seconds)
        return True
    except Exception:
        log.exception("camera ring did not reach %.0f deg, it stands at %.0f deg", degrees, turret.angle)
        return False

# what one look at the rope produced, before the detector has seen any of it
@dataclass(frozen=True)
class Round:
    frames: list            # (camera index, image) for every camera
    captured_at: float      # epoch seconds
    microsteps: int         # where the drive stood when the shutter went
    metres: float


# One look at the rope: a frame from every camera. This is the only part of a round that
# needs the ring standing still
async def capture_round(rt: Runtime) -> Round:
    frames = await asyncio.to_thread(rt.cams.capture)
    # every frame of a round is from the same moment, taking the position per camera would
    # charge cam1 with the inference time of cam0
    return Round(frames, time.time(), rt.drive.microsteps_done, rt.drive.metres_done)


# The detector on what a round saw, and a report for every frame, empty ones included. It
# runs while the ring is already turning: the shutter needs the cameras still, the net does not
async def report_round(rt: Runtime, link: RobotLink, look: Round, seq):
    loop = asyncio.get_running_loop()
    quality = rt.settings.defect_jpeg_quality

    for idx, frame in look.frames:
        started = loop.time()
        found = await asyncio.to_thread(rt.detector.detect, frame)
        # only a frame with something in it is worth storing
        jpeg = await asyncio.to_thread(encode, frame, quality) if found else None
        millis = (loop.time() - started) * 1000.0

        if found:
            summary = ", ".join(
                f"{det.label} {det.confidence:.2f} at ({det.center[0]:.0f}, {det.center[1]:.0f})"
                for det in found
            )
            log.info("cam%d: %d detection(s) in %.0f ms: %s", idx, len(found), millis, summary)
        else:
            log.info("cam%d: nothing detected (%.0f ms)", idx, millis)

        msg = vision_telemetry(
            seq=next(seq),
            cam=idx,
            frame=frame,
            found=found,
            captured_at=look.captured_at,
            microsteps=look.microsteps,
            distance_from_origin=look.metres,
            inference_ms=millis,
            jpeg=jpeg,
        )
        # queued, not sent live: a detection that is not stored is a defect lost
        link.send(msg.model_dump())

# Walk the rope one cycle at a time: look, and turn the cameras a quarter turn while the
# detector works on what was just seen; look again from there, and turn back the same way.
# The drive holds a speed that covers exactly one frame of rope per cycle. While the robot is
# open for a rope socket the ring waits at the angle that clears it and the detector is idle;
# the cycle picks up again where it left off once the robot closes
async def detection_reporter(rt: Runtime, link: RobotLink, stats: DetectionStats,
                             buzzer: Buzzer):
    loop = asyncio.get_running_loop()
    seq = itertools.count(1)
    was_open = rt.rope_socket.is_open

    while True:
        # New settings wait for the robot to rest, and this loop is where it does. Between
        # cycles, drive stopped and ring parked, is the one moment at which the numbers all
        # of the below reads may be swapped out from under it
        rt.flush()
        plan = rt.plan
        open_angle = rt.open_angle

        # the sensor opens the robot on its own, so the sound follows the state and not the
        # command that may never have come
        if rt.rope_socket.is_open != was_open:
            was_open = rt.rope_socket.is_open
            buzzer.play(Sound.OPEN if was_open else Sound.CLOSE)

        # Open for a rope socket: the ring waits at the angle that clears it and no frame
        # goes through the detector. Driving and the video stream carry on
        if rt.rope_socket.is_open:
            # a turn that did not make it leaves the ring off its angle and is tried again,
            # at the pace of a cycle rather than of the poll
            reached = rt.turret.at(open_angle) or await turn_cameras(rt.turret, open_angle)
            rt.rope_socket.close_if_clear(rt.drive.metres_done)
            await asyncio.sleep(rt.settings.open_poll if reached else plan.period)
            continue

        # A standing robot sees the same bit of rope over and over, and inference keeps the
        # Pi hot. The ring rests open while it stands: that covers every way the robot can
        # come to a halt, a stop command as much as a lost link, and leaves it where the
        # next start takes it to be
        if not rt.drive.moving:
            if not rt.turret.at(open_angle):
                await turn_cameras(rt.turret, open_angle)
            await asyncio.sleep(plan.period)
            continue

        # scanning again, so the ring goes to where a cycle starts
        angles = rt.angles
        if not rt.turret.at(angles[0]):
            await turn_cameras(rt.turret, angles[0])

        deadline = loop.time() + plan.period
        try:
            # The ring already stands at the first angle. Every round is taken where it
            # stands and the ring then moves on to the next, the last one back to the first,
            # so the cycle ends where it began with no turn of its own
            for nxt in angles[1:] + angles[:1]:
                # a socket ahead ends the cycle here, no quarter turn is started into it
                if rt.rope_socket.is_open:
                    break
                look = await capture_round(rt)
                await asyncio.gather(
                    turn_cameras(rt.turret, nxt, plan.turn_s),
                    report_round(rt, link, look, seq),
                )
        except Exception:
            log.exception("detection failed")

        # the cycle was cut short for a rope socket: the ring is wanted at the angle that
        # clears it now, not after the rest of a cycle that is not being run
        if rt.rope_socket.is_open:
            continue

        slack = deadline - loop.time()
        stats.cycle_ms = (plan.period - slack) * 1000.0
        if slack < 0.0:
            log.warning("cycle overran its %.0f ms budget by %.0f ms, the rope is not fully covered",
                        plan.period * 1000.0, -slack * 1000.0)
        await asyncio.sleep(max(0.0, slack))

# stop robot when the control link is down
async def link_guard(rt: Runtime, link: RobotLink, motion: MotionController, buzzer: Buzzer):
    stopped = False       # a drive still ramping down is the same fault, not the next one
    while True:
        if not link.connected and rt.drive.moving:
            if not stopped:
                log.warning("control link down while moving => stopping")
                # nobody is watching the webapp for this one, it is the robot's own doing
                buzzer.play(Sound.FAULT)
                stopped = True
            motion.emergency_stop()
        else:
            stopped = False
        await asyncio.sleep(rt.settings.guard_period)

# send motion telemetry
async def telemetry_sender(rt: Runtime, link: RobotLink):
    seq = 0
    while True:
        if link.connected:
            seq += 1
            try:
                msg = MotionTelemetry(
                    speed=rt.drive.speed,
                    speed_mps=rt.drive.speed_mps,
                    microsteps=rt.drive.microsteps_done,
                    metres=rt.drive.metres_done,
                    scan_speed_mps=rt.plan.speed_mps,
                    detect_fps=rt.plan.detect_fps,
                    robot_open=rt.rope_socket.is_open,
                    socket_watch=rt.rope_socket.watch,
                    # the settings really in force, not the ones last received: that is what
                    # lets the webapp say whether a change has taken
                    settings_version=rt.version,
                    seq=seq,
                )
                await link.send_live(msg.model_dump())
            except Exception:
                log.exception("telemetry failed")
        await asyncio.sleep(rt.settings.telemetry_period)

# Read the distance sensor: it watches for the rope socket ahead and its reading is sent on
# as telemetry, live only. The sensor is opened here rather than at startup, so one that was
# not there yet or had a loose contact is picked up later. It is read whether or not the link
# is up, the robot opens for a socket on its own
async def distance_sender(rt: Runtime, link: RobotLink, bus: int):
    tof = None
    seq = 0
    failing = False
    try:
        while True:
            try:
                if tof is None:
                    tof = await asyncio.to_thread(VL53L0X, bus)
                    log.info("distance sensor ready")
                elif failing:
                    # a sensor that dropped out has lost its setup, it has to be set up again
                    await asyncio.to_thread(tof.reset)
                distance = await asyncio.to_thread(tof.read_m)
            except (OSError, RuntimeError) as exc:
                # logged once, a loose wire would otherwise fill the journal twice a second
                if not failing:
                    log.warning("distance sensor not answering: %s", exc)
                failing = True
            else:
                if failing:
                    log.info("distance sensor answers again")
                failing = False
                rt.rope_socket.saw(distance, rt.drive.metres_done)

                if link.connected:
                    seq += 1
                    await link.send_live(DistanceTelemetry(distance_m=distance, seq=seq).model_dump())
            await asyncio.sleep(rt.settings.distance_period)
    finally:
        if tof is not None:
            tof.close()

# redraw the status display
async def display_updater(rt: Runtime, screen: StatusScreen, link: RobotLink, outbox: Outbox,
                          stats: DetectionStats):
    while True:
        status = Status(
            online=link.connected,
            backlog_bytes=outbox.backlog_bytes,
            speed_mps=rt.drive.speed_mps,
            metres=rt.drive.metres_done,
            cycle_ms=stats.cycle_ms,
        )
        try:
            await asyncio.to_thread(screen.show, status)
        except Exception:
            log.exception("display update failed")
        await asyncio.sleep(rt.settings.display_period)

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    task = asyncio.current_task()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, task.cancel)

    # first up, so that the model loading and benchmark below are not a dark screen
    screen = StatusScreen(DISPLAY_I2C_BUS, DISPLAY_ADDRESS, flip=DISPLAY_FLIP)
    screen.message("starting")
    buzzer = Buzzer(BUZZER_PIN)

    # What the robot boots on. The operator's own values arrive from the server as a
    # SettingsCmd once the link is up; until then, and without a server at all, these are
    # the numbers it runs on
    cfg = RobotSettings()

    # configure the drive along the rope
    drive = Drive(
        pul_pin=DRIVE_PUL_PIN,
        dir_pin=DRIVE_DIR_PIN,
        microsteps=cfg.drive_microsteps,
        gear_ratio=cfg.drive_gear_ratio,
        metres_per_rev=cfg.drive_metres_per_rev,
        start_speed=cfg.drive_start_speed,
        max_speed=cfg.drive_max_speed,
        accel=cfg.drive_accel,
    )
    motion = MotionController(drive)

    # configure the ring that turns the cameras. It is parked where it stands now
    turret = Turret(
        pul_pin=TURRET_PUL_PIN,
        dir_pin=TURRET_DIR_PIN,
        microsteps=cfg.turret_microsteps,
        gear_ratio=cfg.turret_gear_ratio,
        max_deg_s=cfg.turret_max_deg_s,
        accel=cfg.turret_accel,
        settle_s=cfg.turret_settle_s,
        start_angle=cfg.turret_open_angle,
    )

    # Configure link to api
    outbox = Outbox("outbox.jsonl")
    link = RobotLink(outbox)
    video = VideoLink()
    cams = CameraPair(
        fps=cfg.camera_fps,
        exposure_us=cfg.camera_exposure_us,
        gain=cfg.camera_gain,
        focus_distance_m=cfg.camera_focus_distance_m,
    ).start()

    # the detector sets the pace the drive runs at, there is no scanning without it
    detector = DetectorProcess()
    await asyncio.to_thread(detector.warmup)
    detector.configure(cfg.detect_confidence, cfg.detect_iou)
    measured = await asyncio.to_thread(measure_cycle, cams, detector, cycles=cfg.benchmark_cycles)

    rope_socket = RopeSocket(cfg.socket_distance_m, cfg.socket_clear_m)
    # holds the settings and everything they decide: the scan plan, the hardware, the pace
    # of every task below
    rt = Runtime(cfg, measured, drive, turret, cams, detector, rope_socket)

    stats = DetectionStats()
    handle = make_command_handler(rt, motion, buzzer)
    link.on_command(handle)

    # a button has no direction of its own, so the red one scans the way StartCmd defaults to
    press = make_button_press(loop, handle)
    buttons = (Button(START_BUTTON_PIN, lambda: press(StartCmd())),
               Button(STOP_BUTTON_PIN, lambda: press(StopCmd())))

    log.info("steppers, buttons, detector and link configured")
    # the startup takes long enough that the operator needs telling when it is over
    buzzer.play(Sound.READY)

    # kick off tasks, accept signals (shutdown if received)
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(link.run(), name="control-link")
            tg.create_task(video.run(), name="video-link")
            tg.create_task(frame_producer(rt, video), name="frame-stream")
            tg.create_task(detection_reporter(rt, link, stats, buzzer), name="detection")
            tg.create_task(link_guard(rt, link, motion, buzzer), name="guard")
            tg.create_task(telemetry_sender(rt, link), name="telemetry")
            tg.create_task(distance_sender(rt, link, TOF_I2C_BUS), name="distance")
            tg.create_task(display_updater(rt, screen, link, outbox, stats), name="display")
    except* asyncio.CancelledError:
        log.info("shutting down")
    finally:
        motion.emergency_stop()
        # then the buttons, so that nothing more can be asked of a robot being torn down
        for button in buttons:
            button.close()
        buzzer.close()
        cams.close()
        turret.close()
        motion.shutdown()
        screen.close()
        log.info("stopped")

if __name__ == "__main__":
    asyncio.run(main())
