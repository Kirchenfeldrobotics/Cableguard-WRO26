import asyncio 
from fastapi import WebSocket

class Hub: 
    def __init__(self): 
        self._robot = None   # Robot Websocket
        self._uis   = set()  # Browser Websockets
        self._lock  = asyncio.Lock()

    # set _robot to websocket
    async def attach_robot(self, sock): 
        async with self._lock: 
            if self._robot is not None: 
                await self._robot.close(code=1012)
            self._robot = sock 
        await self.broadcast({"type": "robot_status", "online": True})

    # remove websocket from _robot
    async def detach_robot(self, sock): 
        async with self._lock: 
            if self._robot is sock: 
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
        deads = []
        for ui in targets: 
            try: 
                await ui.send_json(msg)
            except Exception: 
                await dead.append(ui)

        for dead in deads: 
            await self.remove_ui(ui)

    # send message to robot
    async def to_robot(self, msg): 
        async with self._lock: 
            robot = self._robot
        if robot is None: 
            return False 
        try: 
            robot.send_json(msg)
            return True
        except Exception: 
            return False

hub = Hub()