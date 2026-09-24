import asyncio 
import time
from fastapi import WebSocket

SEND_TIMEOUT = 1.0

# The robot reports its motion twice a second. Past this the last report says nothing about
# what it is doing now, and a connected robot that has gone quiet is not one to reconfigure
MOTION_STALE_S = 5.0

class Hub:
    def __init__(self): 
        self._robot = None   # Robot Websocket
        self._uis   = set()  # Browser Websockets
        self._lock  = asyncio.Lock()

        # last motion the robot reported, and when. Only the settings route reads it, to
        # refuse a change to a robot that is driving
        self._speed    = None
        self._speed_at = 0.0

    # set _robot to websocket
    async def attach_robot(self, sock): 
        async with self._lock: 
            if self._robot is not None: 
                try:
                    await asyncio.wait_for(self._robot.close(code=1012), timeout=SEND_TIMEOUT)
                except Exception:
                    pass
            self._robot = sock 
        await self.broadcast({"type": "robot_status", "online": True})

    # remove websocket from _robot
    async def detach_robot(self, sock): 
        async with self._lock: 
            if self._robot is not sock:
                return
            self._robot = None
            # what the robot was doing before it went is no guide to what the next one does
            self._speed = None
        await self.broadcast({"type": "robot_status", "online": False})

    # the speed out of the last motion telemetry, kept for the settings route
    def note_motion(self, speed): 
        self._speed    = speed
        self._speed_at = time.monotonic()

    # Why the settings may not be changed right now, or None. The robot takes a whole set
    # at once and some of it redefines the position it is counting in, so a change is only
    # offered to a robot that stands still. One that is offline moves nothing and gets the
    # new set the moment it connects
    def settings_locked(self): 
        if self._robot is None: 
            return None
        if self._speed is None or time.monotonic() - self._speed_at > MOTION_STALE_S: 
            return "the robot has not reported whether it is moving"
        if self._speed != 0.0: 
            return "the robot is moving, stop it before changing its settings"
        return None

    # add a ui client to the set 
    async def add_ui(self, sock): 
        async with self._lock: 
            self._uis.add(sock)
        await sock.send_json({"type": "robot_status", "online": self._robot is not None})

    # remove a ui client from the set
    async def remove_ui(self, sock):
        async with self._lock: 
            self._uis.discard(sock) 

    # broadcast message to all ui clients 
    async def broadcast(self, msg): 
        async with self._lock: 
            targets = list(self._uis)
        dead = []
        for ui in targets: 
            try: 
                await asyncio.wait_for(ui.send_json(msg), timeout=SEND_TIMEOUT)
            except Exception:
                dead.append(ui)

        for ui in dead:
            await self.remove_ui(ui)
            try:
                await asyncio.wait_for(ui.close(), timeout=SEND_TIMEOUT)
            except Exception:
                pass

    # send message to robot
    async def to_robot(self, msg): 
        async with self._lock: 
            robot = self._robot
        if robot is None: 
            return False 
        try: 
            await robot.send_json(msg)
            return True
        except Exception: 
            return False

hub = Hub()