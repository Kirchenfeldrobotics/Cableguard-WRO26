from __future__ import annotations 

import asyncio
import logging 
import os 
import signal 

from comm_protocols.messages import SpeedCmd, StopCmd

from camera.camera import CameraPair #, encode
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

# creates function that handles cmds
