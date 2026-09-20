from __future__ import annotations 

import asyncio
import logging
import signal
import time

from comm_protocols.messages import MotionTelemetry, ResetOriginCmd, StartCmd, StopCmd

from camera.camera import CameraPair, encode
from link.client import RobotLink
from link.outbox import Outbox
from link.video import VideoLink
from motion.controller import MotionController
from motion.stepper import Stepper
from vision.detector import Detector
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

GUARD_PERIOD = 0.5
TELEMETRY_PERIOD = 0.5

# creates function that turns messages into roboter commands. The speed is not ours to
# choose, the scan plan fixed it so that the detector sees every bit of rope once
def make_command_handler(motion: MotionController, plan: ScanPlan): 
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

# run the detector on both cameras, write what it sees to the journal and report it
async def detection_reporter(cams: CameraPair, detector: Detector, link: RobotLink, motor: Stepper, period: float):
    loop = asyncio.get_running_loop()
    seq = 0

    while True:
        deadline = loop.time() + period
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
                millis = (loop.time() - started) * 1000.0

                if found:
                    summary = ", ".join(
                        f"{det.label} {det.confidence:.2f} at ({det.center[0]:.0f}, {det.center[1]:.0f})"
                        for det in found
                    )
                    log.info("cam%d: %d detection(s) in %.0f ms: %s", idx, len(found), millis, summary)
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
                )
                # queued, not sent live: a detection that is not stored is a defect lost
                link.send(msg.model_dump())
        except Exception:
            log.exception("detection failed")

        slack = deadline - loop.time()
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

async def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    task = asyncio.current_task()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, task.cancel)

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
    video = VideoLink()
    cams = CameraPair(fps=CAMERA_FPS).start()

    # the detector sets the pace the drive runs at, there is no scanning without it
    detector = Detector()
    await asyncio.to_thread(detector.warmup)
    cycle_s = await asyncio.to_thread(measure_cycle, cams, detector)

    # the drive can only be asked for speeds it can actually hold
    plan = plan_scan(
        cycle_s=cycle_s,
        camera_fps=CAMERA_FPS,
        speed_limits=(motor.to_metres(motor.start_speed), motor.to_metres(motor.max_speed)),
    )

    link.on_command(make_command_handler(motion, plan))

    log.info("stepper, detector and link configured")

    # kick off tasks, accept signals (shutdown if received)
    try: 
        async with asyncio.TaskGroup() as tg: 
            tg.create_task(link.run(), name="control-link")
            tg.create_task(video.run(), name="video-link")
            tg.create_task(frame_producer(cams, video, STEAM_FPS), name="frame-stream")
            tg.create_task(detection_reporter(cams, detector, link, motor, plan.period), name="detection")
            tg.create_task(link_guard(link, motion), name="guard")
            tg.create_task(telemetry_sender(link, motor, plan, TELEMETRY_PERIOD), name="telemetry")
    except* asyncio.CancelledError:
        log.info("shutting down")
    finally: 
        motion.emergency_stop()
        cams.close()
        motion.shutdown()
        log.info("stopped")

if __name__ == "__main__": 
    asyncio.run(main())