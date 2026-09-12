from __future__ import annotations 

import asyncio
import logging 
import os 
import signal 

from comm_protocols.messages import SpeedCmd, StopCmd

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

VIDEO_URL = os.environ["VIDEO_WS_URL"]
TOKEN = os.environ["CABLEGUARD_ROBOT_TOKEN"]

GUARD_PERIOD = 0.5

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

    while True: 
        try: 
            for idx, lores in cams.capture_lores(): 
                video.submit(idx, encode(lores))
        except Exception: 
            log.exception("log capture failed")
        await asyncio.sleep(period)

# stop robot when the control link is down
async def link_guard(link: RobotLink, motion: MotionController):
    while True: 
        if not link.connected and motion.motor.moving: 
            log.warning("control link down while moving => stopping") 
            motion.emergency_stop()
        await asyncio.sleep(GUARD_PERIOD)

# throw exception when script is killed/interrupted by signal
async def _wait_for_signal(stop: asyncio.Event): 
    await stop.wait()
    raise asyncio.CancelledError("shutdown requested")

async def main(): 
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT): 
        loop.add_signal_handler(sig, stop.set)

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
    video = VideoLink(fps=STEAM_FPS)
    cams = CameraPair(fps=CAMERA_FPS)

    link.on_command(make_command_handler(motion))

    log.info("stepper and link configured")

    # kick off tasks, accept signals (shutdown if received)
    try: 
        async with asyncio.TaskGroup() as tg: 
            tg.create_task(link.run(), name="control-link")
            tg.create_task(video.run(), name="video-link")
            tg.create_task(frame_producer(cams, video, STEAM_FPS), name="frame-stream")
            tg.create_task(link_guard(link, motion), name="guard")
            tg.create_task(_wait_for_signal(stop), name="signal")
    except* asyncio.CancelledError:
        log.info("shutting down")
    finally: 
        motion.emergency_stop()
        cams.close()
        motion.shutdown()
        log.info("stopped")

if __name__ == "__main__": 
    asyncio.run(main())