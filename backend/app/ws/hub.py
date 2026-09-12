import asyncio 
from fastapi import WebSocket

SEND_TIMEOUT = 1.0

class Hub:
    def __init__(self): 
        self._robot = None   # Robot Websocket
        self._uis   = set()  # Browser Websockets
        self._lock  = asyncio.Lock()

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
        await self.broadcast({"type": "robot_status", "online": False})

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