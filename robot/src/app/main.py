from __future__ import annotations 

import asyncio
import logging
import signal
import time
from dataclasses import dataclass

from comm_protocols.messages import DistanceTelemetry, MotionTelemetry, ResetOriginCmd, StartCmd, StopCmd

from camera.camera import CameraPair, encode
from display.screen import Status, StatusScreen
from link.client import RobotLink
from link.outbox import Outbox
from link.video import VideoLink
from motion.controller import MotionController
from motion.stepper import Stepper
from tof.vl53l0x import VL53L0X
from vision.detector import DetectorProcess
from vision.pacing import ScanPlan, measure_cycle, plan_scan
from vision.report import vision_telemetry

log = logging.getLogger("cableguard")

# configuration

PUL_PIN = 18
DIR_PIN = 23
MICROSTEPS = 8 
MAX_SPEED = 2000.0
ACCEL = 4000.0

STEAM_FPS = 8.0
CAMERA_FPS = 15.0

# the frame a defect was found in is kept as evidence, sharp enough to see a single wire
DEFECT_JPEG_QUALITY = 85

GUARD_PERIOD = 0.5
TELEMETRY_PERIOD = 0.5

# distance sensor, a TOF200C (VL53L0X) on I2C bus 1 (SDA GPIO2, SCL GPIO3)
TOF_I2C_BUS = 1
DISTANCE_PERIOD = 0.5
# status display, a 1.54" ST7789 on SPI0 (SCL GPIO11, SDA GPIO10, CS GPIO8)
DISPLAY_DC_PIN = 25
DISPLAY_RST_PIN = 27
DISPLAY_BL_PIN = 24
DISPLAY_ROTATION = 90       # 270 if the picture stands on its head
DISPLAY_PERIOD = 1.0

# creates function that turns messages into roboter commands. The speed is not ours to
# choose, the scan plan fixed it so that the detector sees every bit of rope once
def make_command_handler(motion: MotionController, plan: ScanPlan, stats: DetectionStats): 
    # the round trip through metres is not bit exact, and ramp_to reads anything below
    # start_speed as a stop, so a plan sitting on the lower limit must not fall through it
    scan_speed = max(motion.motor.to_microsteps(plan.speed_mps), motion.motor.start_speed)

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
            if motion.motor.moving: 
                log.warning("origin reset while moving, the run starts from here anyway")
            log.info("origin reset at %.2f m", motion.motor.metres_done)
            motion.motor.reset_steps_done()
            stats.new_run()

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

# what the detector has found in the current run, for the status display
@dataclass
class DetectionStats:
    count: int = 0
    last: str | None = None           # label and confidence of the latest defect
    last_at: float | None = None      # time.monotonic() of it
    cycle_ms: float | None = None     # how long the last detector cycle took

    # a run starts at its origin, the detector timing carries over
    def new_run(self):
        self.count = 0
        self.last = None
        self.last_at = None

# run the detector on both cameras, write what it sees to the journal and report it
async def detection_reporter(cams: CameraPair, detector: DetectorProcess, link: RobotLink, motor: Stepper,
                             stats: DetectionStats, period: float):
    loop = asyncio.get_running_loop()
    seq = 0

    while True:
        deadline = loop.time() + period
        # a standing robot sees the same bit of rope over and over, and inference keeps the Pi hot
        if not motor.moving:
            await asyncio.sleep(period)
            continue
        try:
            frames = await asyncio.to_thread(cams.capture)
            # both frames are from the same moment, taking the position per camera would
            # charge cam1 with the inference time of cam0
            captured_at = time.time()
            microsteps  = motor.microsteps_done
            distance    = motor.metres_done

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
                    best = max(found, key=lambda det: det.confidence)
                    stats.count += len(found)
                    stats.last = f"{best.label} {best.confidence:.2f}"
                    stats.last_at = time.monotonic()
                else:
                    log.info("cam%d: nothing detected (%.0f ms)", idx, millis)

                seq += 1
                msg = vision_telemetry(
                    seq=seq,
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
        except Exception:
            log.exception("detection failed")

        slack = deadline - loop.time()
        stats.cycle_ms = (period - slack) * 1000.0
        if slack < 0.0:
            log.warning("cycle overran its %.0f ms budget by %.0f ms, the rope is not fully covered",
                        period * 1000.0, -slack * 1000.0)
        await asyncio.sleep(max(0.0, slack))

# stop robot when the control link is down
async def link_guard(link: RobotLink, motion: MotionController):
    while True: 
        if not link.connected and motion.motor.moving: 
            log.warning("control link down while moving => stopping") 
            motion.emergency_stop()
        await asyncio.sleep(GUARD_PERIOD)

# send motion telemetry
async def telemetry_sender(link: RobotLink, motor: Stepper, plan: ScanPlan, period: float):
    seq = 0
    while True:
        if link.connected:
            seq += 1
            try:
                msg = MotionTelemetry(
                    speed=motor.speed,
                    speed_mps=motor.speed_mps,
                    microsteps=motor.microsteps_done,
                    metres=motor.metres_done,
                    scan_speed_mps=plan.speed_mps,
                    detect_fps=plan.detect_fps,
                    seq=seq,
                )
                await link.send_live(msg.model_dump())
            except Exception:
                log.exception("telemetry failed")
        await asyncio.sleep(period)

# send what the distance sensor sees, live only
async def distance_sender(link: RobotLink, tof: VL53L0X, period: float):
    seq = 0
    failing = False
    while True:
        if link.connected:
            try:
                # a sensor that dropped out has lost its setup, it has to be set up again
                if failing:
                    await asyncio.to_thread(tof.reset)
                distance = await asyncio.to_thread(tof.read_m)
            except (OSError, RuntimeError) as exc:
                # logged once, a loose wire would otherwise fill the journal twice a second
                if not failing:
                    log.warning("distance sensor stopped answering: %s", exc)
                failing = True
            else:
                if failing:
                    log.info("distance sensor answers again")
                failing = False
                seq += 1
                await link.send_live(DistanceTelemetry(distance_m=distance, seq=seq).model_dump())
# redraw the status display
async def display_updater(screen: StatusScreen, link: RobotLink, outbox: Outbox, motor: Stepper,
                          stats: DetectionStats, period: float):
    while True:
        status = Status(
            online=link.connected,
            backlog_bytes=outbox.backlog_bytes,
            speed_mps=motor.speed_mps,
            metres=motor.metres_done,
            defects=stats.count,
            last_defect=stats.last,
            last_defect_at=stats.last_at,
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
    screen = StatusScreen(DISPLAY_DC_PIN, DISPLAY_RST_PIN, DISPLAY_BL_PIN, rotation=DISPLAY_ROTATION)
    screen.message("starting")

    # configure stepper
    motor = Stepper(
        pul_pin=PUL_PIN, 
        dir_pin=DIR_PIN, 
        microsteps=MICROSTEPS, 
        max_speed=MAX_SPEED, 
        accel=ACCEL
    )
    motion = MotionController(motor)

    # Configure link to api 
    outbox = Outbox("outbox.jsonl")
    link = RobotLink(outbox)

    # distance to the next object, the robot runs without it
    try:
        tof = VL53L0X(TOF_I2C_BUS)
    except (OSError, RuntimeError) as exc:
        log.warning("no distance sensor: %s", exc)
        tof = None

    video = VideoLink()
    cams = CameraPair(fps=CAMERA_FPS).start()

    # the detector sets the pace the drive runs at, there is no scanning without it
    detector = DetectorProcess()
    await asyncio.to_thread(detector.warmup)
    cycle_s = await asyncio.to_thread(measure_cycle, cams, detector)

    # the drive can only be asked for speeds it can actually hold
    plan = plan_scan(
        cycle_s=cycle_s,
        camera_fps=CAMERA_FPS,
        speed_limits=(motor.to_metres(motor.start_speed), motor.to_metres(motor.max_speed)),
    )

    stats = DetectionStats()
    link.on_command(make_command_handler(motion, plan, stats))

    log.info("stepper, detector and link configured")

    # kick off tasks, accept signals (shutdown if received)
    try: 
        async with asyncio.TaskGroup() as tg: 
            tg.create_task(link.run(), name="control-link")
            tg.create_task(video.run(), name="video-link")
            tg.create_task(frame_producer(cams, video, STEAM_FPS), name="frame-stream")
            tg.create_task(detection_reporter(cams, detector, link, motor, stats, plan.period), name="detection")
            tg.create_task(link_guard(link, motion), name="guard")
            tg.create_task(telemetry_sender(link, motor, plan, TELEMETRY_PERIOD), name="telemetry")
            if tof is not None:
                tg.create_task(distance_sender(link, tof, DISTANCE_PERIOD), name="distance")
            tg.create_task(display_updater(screen, link, outbox, motor, stats, DISPLAY_PERIOD), name="display")
    except* asyncio.CancelledError:
        log.info("shutting down")
    finally: 
        motion.emergency_stop()
        cams.close()
        motion.shutdown()
        if tof is not None:
            tof.close()
        screen.close()
        log.info("stopped")

if __name__ == "__main__": 
    asyncio.run(main())