from __future__ import annotations 

import asyncio
import logging
import signal

from comm_protocols.messages import MotionTelemetry, SpeedCmd, StopCmd

from camera.camera import CameraPair, encode
from link.client import RobotLink
from link.outbox import Outbox
from link.video import VideoLink
from motion.controller import MotionController
from motion.stepper import Stepper

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

    link.on_command(make_command_handler(motion))

    log.info("stepper and link configured")

    # kick off tasks, accept signals (shutdown if received)
    try: 
        async with asyncio.TaskGroup() as tg: 
            tg.create_task(link.run(), name="control-link")
            tg.create_task(video.run(), name="video-link")
            tg.create_task(frame_producer(cams, video, STEAM_FPS), name="frame-stream")
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