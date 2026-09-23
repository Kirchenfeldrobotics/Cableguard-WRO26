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
    SocketWatchCmd,
    StartCmd,
    StopCmd,
)

from app.ropesocket import RopeSocket
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
from vision.pacing import ScanPlan, measure_cycle, plan_scan
from vision.report import vision_telemetry

log = logging.getLogger("cableguard")

# configuration

# the stepper that moves the robot along the rope
DRIVE_PUL_PIN   = 18
DRIVE_DIR_PIN   = 23
DRIVE_MICROSTEPS = 8
DRIVE_MAX_SPEED = 2000.0
DRIVE_ACCEL     = 4000.0

# the stepper that swings both cameras around the rope
TURRET_PUL_PIN   = 12
TURRET_DIR_PIN   = 16
TURRET_MICROSTEPS = 8
TURRET_GEAR_RATIO = 1.0         # motor turns for one turn of the ring
TURRET_MAX_SPEED  = 2000.0
TURRET_ACCEL      = 20000.0     # the ring is light, it may be ramped harder than the drive

# Where the cameras look from, degrees from the parked position. Two cameras facing each
# other cover two sides of the rope, a quarter turn puts them on the other two. The ring
# starts and ends every cycle parked, so it never winds up the camera cables
TURRET_ANGLES = (0.0, 90.0)

# Where the ring parks while the robot is open. A rope socket is the fitting the rope ends
# in, and the robot only clears one with the cameras swung out of the way
TURRET_OPEN_ANGLE = 20.0

# Anything the distance sensor sees closer than this counts as a rope socket ahead. Far
# enough that the robot is still open before it arrives, close enough that the rope itself
# and the odd branch do not keep opening it
SOCKET_DISTANCE_M = 0.30

# Driven from where the sensor last saw the socket, this puts it behind the robot
SOCKET_CLEAR_M = 0.50

# How often an open robot looks at whether it may close again
OPEN_POLL = 0.25

STEAM_FPS = 8.0
CAMERA_FPS = 15.0

# the frame a defect was found in is kept as evidence, sharp enough to see a single wire
DEFECT_JPEG_QUALITY = 85

GUARD_PERIOD = 0.5
TELEMETRY_PERIOD = 0.5

# distance sensor, a TOF200C (VL53L0X) on I2C bus 1 (SDA GPIO2, SCL GPIO3)
TOF_I2C_BUS = 1
DISTANCE_PERIOD = 0.5
# status display, a 0.96" 128x64 SSD1306 OLED. It shares I2C bus 1 with the distance sensor
DISPLAY_I2C_BUS = 1
DISPLAY_ADDRESS = 0x3C      # 0x3D on boards where the address pad is bridged
DISPLAY_FLIP = False        # True if the panel is mounted upside down
DISPLAY_PERIOD = 1.0

# creates function that turns messages into roboter commands. The speed is not ours to
# choose, the scan plan fixed it so that the detector sees every bit of rope once
def make_command_handler(motion: MotionController, plan: ScanPlan, rope_socket: RopeSocket): 
    # the round trip through metres is not bit exact, and ramp_to reads anything below
    # start_speed as a stop, so a plan sitting on the lower limit must not fall through it
    scan_speed = max(motion.drive.to_microsteps(plan.speed_mps), motion.drive.start_speed)

    def handle(cmd): 
        if isinstance(cmd, StopCmd): 
            log.info("stop requested")
            motion.emergency_stop()

        elif isinstance(cmd, StartCmd): 
            target = scan_speed if cmd.direction == "forward" else -scan_speed
            log.info("start requested: %s at %.3f m/s (%.0f microsteps/s)",
                     cmd.direction, plan.speed_mps, scan_speed)
            motion.request("speed", target)

        elif isinstance(cmd, ResetOriginCmd): 
            if motion.drive.moving:
                log.warning("origin reset while moving, the run starts from here anyway")
            log.info("origin reset at %.2f m", motion.drive.metres_done)
            motion.drive.reset_steps_done()
            # the clear distance is measured from a position that just became zero
            rope_socket.rebase(motion.drive.metres_done)

        elif isinstance(cmd, OpenCmd): 
            rope_socket.open_by_user()

        elif isinstance(cmd, CloseCmd): 
            rope_socket.close_by_user()

        elif isinstance(cmd, SocketWatchCmd): 
            rope_socket.set_watch(cmd.enabled)

    return handle

# capture frames (streaming res.), encode, hand them to the video link 
async def frame_producer(cams: CameraPair, video: VideoLink, fps: float): 
    period = 1.0 / fps
    loop = asyncio.get_running_loop()

    while True:
        deadline = loop.time() + period
        try:
            for idx, lores in await asyncio.to_thread(cams.capture_lores):
                video.submit(idx, encode(lores))
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

# One look at the rope: a frame from every camera, the detector on each of them, and a
# report for every frame, empty ones included
async def scan_round(cams: CameraPair, detector: DetectorProcess, link: RobotLink, drive: Drive,
                     seq):
    loop = asyncio.get_running_loop()

    frames = await asyncio.to_thread(cams.capture)
    # both frames are from the same moment, taking the position per camera would
    # charge cam1 with the inference time of cam0
    captured_at = time.time()
    microsteps  = drive.microsteps_done
    distance    = drive.metres_done

    for idx, frame in frames:
        started = loop.time()
        found = await asyncio.to_thread(detector.detect, frame)
        # only a frame with something in it is worth storing
        jpeg = await asyncio.to_thread(encode, frame, DEFECT_JPEG_QUALITY) if found else None
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
            captured_at=captured_at,
            microsteps=microsteps,
            distance_from_origin=distance,
            inference_ms=millis,
            jpeg=jpeg,
        )
        # queued, not sent live: a detection that is not stored is a defect lost
        link.send(msg.model_dump())

# Walk the rope one cycle at a time: look, turn the cameras a quarter turn, look again, turn
# back. The drive holds a speed that covers exactly one frame of rope per cycle. While the
# robot is open for a rope socket the ring waits at the angle that clears it and the detector
# is idle; the cycle picks up again where it left off once the robot closes
async def detection_reporter(cams: CameraPair, detector: DetectorProcess, link: RobotLink, drive: Drive,
                             turret: Turret, rope_socket: RopeSocket, stats: DetectionStats,
                             plan: ScanPlan):
    loop = asyncio.get_running_loop()
    seq = itertools.count(1)

    while True:
        # Open for a rope socket: the ring waits at the angle that clears it and no frame
        # goes through the detector. Driving and the video stream carry on
        if rope_socket.is_open:
            # a turn that did not make it leaves the ring off its angle and is tried again,
            # at the pace of a cycle rather than of the poll
            reached = turret.at(TURRET_OPEN_ANGLE) or await turn_cameras(turret, TURRET_OPEN_ANGLE)
            rope_socket.close_if_clear(drive.metres_done)
            await asyncio.sleep(OPEN_POLL if reached else plan.period)
            continue

        # closed again, so the ring goes back to where a cycle starts
        if not turret.at(TURRET_ANGLES[0]):
            await turn_cameras(turret, TURRET_ANGLES[0])

        # a standing robot sees the same bit of rope over and over, and inference keeps the Pi hot
        if not drive.moving:
            await asyncio.sleep(plan.period)
            continue

        deadline = loop.time() + plan.period
        try:
            for angle in TURRET_ANGLES:
                # a socket ahead ends the cycle here, no quarter turn is started into it
                if rope_socket.is_open:
                    break
                await turn_cameras(turret, angle, plan.turn_s)
                await scan_round(cams, detector, link, drive, seq)

            if not rope_socket.is_open:
                # parked again, where the next cycle expects the cameras to be
                await turn_cameras(turret, TURRET_ANGLES[0], plan.turn_s)
        except Exception:
            log.exception("detection failed")

        # the cycle was cut short for a rope socket: the ring is wanted at the angle that
        # clears it now, not after the rest of a cycle that is not being run
        if rope_socket.is_open:
            continue

        slack = deadline - loop.time()
        stats.cycle_ms = (plan.period - slack) * 1000.0
        if slack < 0.0:
            log.warning("cycle overran its %.0f ms budget by %.0f ms, the rope is not fully covered",
                        plan.period * 1000.0, -slack * 1000.0)
        await asyncio.sleep(max(0.0, slack))

# stop robot when the control link is down
async def link_guard(link: RobotLink, motion: MotionController):
    while True: 
        if not link.connected and motion.drive.moving:
            log.warning("control link down while moving => stopping") 
            motion.emergency_stop()
        await asyncio.sleep(GUARD_PERIOD)

# send motion telemetry
async def telemetry_sender(link: RobotLink, drive: Drive, plan: ScanPlan, rope_socket: RopeSocket,
                           period: float):
    seq = 0
    while True:
        if link.connected:
            seq += 1
            try:
                msg = MotionTelemetry(
                    speed=drive.speed,
                    speed_mps=drive.speed_mps,
                    microsteps=drive.microsteps_done,
                    metres=drive.metres_done,
                    scan_speed_mps=plan.speed_mps,
                    detect_fps=plan.detect_fps,
                    robot_open=rope_socket.is_open,
                    socket_watch=rope_socket.watch,
                    seq=seq,
                )
                await link.send_live(msg.model_dump())
            except Exception:
                log.exception("telemetry failed")
        await asyncio.sleep(period)

# Read the distance sensor: it watches for the rope socket ahead and its reading is sent on
# as telemetry, live only. The sensor is opened here rather than at startup, so one that was
# not there yet or had a loose contact is picked up later. It is read whether or not the link
# is up, the robot opens for a socket on its own
async def distance_sender(link: RobotLink, drive: Drive, rope_socket: RopeSocket, bus: int, period: float):
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
                rope_socket.saw(distance, drive.metres_done)

                if link.connected:
                    seq += 1
                    await link.send_live(DistanceTelemetry(distance_m=distance, seq=seq).model_dump())
            await asyncio.sleep(period)
    finally:
        if tof is not None:
            tof.close()

# redraw the status display
async def display_updater(screen: StatusScreen, link: RobotLink, outbox: Outbox, drive: Drive,
                          stats: DetectionStats, period: float):
    while True:
        status = Status(
            online=link.connected,
            backlog_bytes=outbox.backlog_bytes,
            speed_mps=drive.speed_mps,
            metres=drive.metres_done,
            cycle_ms=stats.cycle_ms,
        )
        try:
            await asyncio.to_thread(screen.show, status)
        except Exception:
            log.exception("display update failed")
        await asyncio.sleep(period)

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    task = asyncio.current_task()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, task.cancel)

    # first up, so that the model loading and benchmark below are not a dark screen
    screen = StatusScreen(DISPLAY_I2C_BUS, DISPLAY_ADDRESS, flip=DISPLAY_FLIP)
    screen.message("starting")

    # configure the drive along the rope
    drive = Drive(
        pul_pin=DRIVE_PUL_PIN,
        dir_pin=DRIVE_DIR_PIN,
        microsteps=DRIVE_MICROSTEPS,
        max_speed=DRIVE_MAX_SPEED,
        accel=DRIVE_ACCEL
    )
    motion = MotionController(drive)

    # configure the ring that turns the cameras. It is parked where it stands now
    turret = Turret(
        pul_pin=TURRET_PUL_PIN,
        dir_pin=TURRET_DIR_PIN,
        microsteps=TURRET_MICROSTEPS,
        gear_ratio=TURRET_GEAR_RATIO,
        max_speed=TURRET_MAX_SPEED,
        accel=TURRET_ACCEL,
    )

    # Configure link to api 
    outbox = Outbox("outbox.jsonl")
    link = RobotLink(outbox)
    video = VideoLink()
    cams = CameraPair(fps=CAMERA_FPS).start()

    # the detector sets the pace the drive runs at, there is no scanning without it
    detector = DetectorProcess()
    await asyncio.to_thread(detector.warmup)
    cycle_s = await asyncio.to_thread(measure_cycle, cams, detector)

    # the drive can only be asked for speeds it can actually hold, and the cycle only for
    # turns the ring manages in the time it is given
    plan = plan_scan(
        cycle_s=cycle_s,
        camera_fps=CAMERA_FPS,
        speed_limits=(drive.to_metres(drive.start_speed), drive.to_metres(drive.max_speed)),
        min_turn_s=turret.min_turn_s(TURRET_ANGLES[1] - TURRET_ANGLES[0]),
    )

    stats = DetectionStats()
    rope_socket = RopeSocket(SOCKET_DISTANCE_M, SOCKET_CLEAR_M)
    link.on_command(make_command_handler(motion, plan, rope_socket))

    log.info("steppers, detector and link configured")

    # kick off tasks, accept signals (shutdown if received)
    try: 
        async with asyncio.TaskGroup() as tg: 
            tg.create_task(link.run(), name="control-link")
            tg.create_task(video.run(), name="video-link")
            tg.create_task(frame_producer(cams, video, STEAM_FPS), name="frame-stream")
            tg.create_task(detection_reporter(cams, detector, link, drive, turret, rope_socket,
                                              stats, plan), name="detection")
            tg.create_task(link_guard(link, motion), name="guard")
            tg.create_task(telemetry_sender(link, drive, plan, rope_socket, TELEMETRY_PERIOD),
                           name="telemetry")
            tg.create_task(distance_sender(link, drive, rope_socket, TOF_I2C_BUS, DISTANCE_PERIOD),
                           name="distance")
            tg.create_task(display_updater(screen, link, outbox, drive, stats, DISPLAY_PERIOD), name="display")
    except* asyncio.CancelledError:
        log.info("shutting down")
    finally: 
        motion.emergency_stop()
        cams.close()
        turret.close()
        motion.shutdown()
        screen.close()
        log.info("stopped")

if __name__ == "__main__": 
    asyncio.run(main())
