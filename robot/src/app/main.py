from __future__ import annotations 

import asyncio
import logging
import signal
from typing import TYPE_CHECKING

from comm_protocols.messages import MotionTelemetry, SpeedCmd, StopCmd

from camera.camera import CameraPair, encode
from link.client import RobotLink
from link.outbox import Outbox
from link.video import VideoLink
from motion.controller import MotionController
from motion.stepper import Stepper

if TYPE_CHECKING:
    from vision.detector import Detector

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
DETECT_PERIOD = 2.0

# creates function that turns messages into roboter commands
def make_command_handler(motion: MotionController): 
    def handle(cmd): 
        if isinstance(cmd, StopCmd): 
            log.info("stop requested")
            motion.emergency_stop()

        elif isinstance(cmd, SpeedCmd): 
            limit = motion.motor.max_speed
            target = max(-limit, min(cmd.value, limit))
            log.info("speed requested: %.0f (clamped to: %.0f)", cmd.value, target)
            motion.request("speed", target)

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

# run the detector on both cameras and write what it sees to the journal
async def detection_logger(cams: CameraPair, detector: Detector, period: float):
    loop = asyncio.get_running_loop()

    while True:
        deadline = loop.time() + period
        try:
            for idx, frame in await asyncio.to_thread(cams.capture):
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
        except Exception:
            log.exception("detection failed")
        await asyncio.sleep(max(0.0, deadline - loop.time()))

# stop robot when the control link is down
async def link_guard(link: RobotLink, motion: MotionController):
    while True: 
        if not link.connected and motion.motor.moving: 
            log.warning("control link down while moving => stopping") 
            motion.emergency_stop()
        await asyncio.sleep(GUARD_PERIOD)

# send motion telemetry
async def telemetry_sender(link: RobotLink, motor: Stepper, period: float):
    seq = 0
    while True:
        if link.connected:
            seq += 1
            try:
                msg = MotionTelemetry(speed=motor.speed, microsteps=motor.microsteps_done, seq=seq)
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

    # vision is optional, a broken model or a missing package must not stop the robot from driving
    try:
        from vision.detector import Detector

        detector = Detector()
        await asyncio.to_thread(detector.warmup)
    except Exception as exc:
        detector = None
        log.warning("detection disabled, detector unavailable: %s", exc)

    link.on_command(make_command_handler(motion))

    log.info("stepper and link configured, detection %s", "on" if detector else "off")

    # kick off tasks, accept signals (shutdown if received)
    try: 
        async with asyncio.TaskGroup() as tg: 
            tg.create_task(link.run(), name="control-link")
            tg.create_task(video.run(), name="video-link")
            tg.create_task(frame_producer(cams, video, STEAM_FPS), name="frame-stream")
            if detector is not None:
                tg.create_task(detection_logger(cams, detector, DETECT_PERIOD), name="detection-log")
            tg.create_task(link_guard(link, motion), name="guard")
            tg.create_task(telemetry_sender(link, motor, TELEMETRY_PERIOD), name="telemetry")
    except* asyncio.CancelledError:
        log.info("shutting down")
    finally: 
        motion.emergency_stop()
        cams.close()
        motion.shutdown()
        log.info("stopped")

if __name__ == "__main__": 
    asyncio.run(main())