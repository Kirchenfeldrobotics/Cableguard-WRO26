import asyncio
import logging 

from fastapi import WebSocket 

log = logging.getLogger(__name__)

SEND_TIMEOUT = 0.1 

class VideoHub: 
    def __init__(self): 
        self._viewers      = set()
        self._lock         = asyncio.Lock()
        self._robot_online = False

    async def add_viewer(self, sock): 
        async with self._lock: 
            self._viewers.add(sock)

    async def remove_viewer(self, sock): 
        async with self._lock: 
            self._viewers.discard(sock)

    async def set_robot(self, is_online): 
        async with self._lock: 
            self._robot_online = is_online

    @property
    def viewer_count(self): 
        return len(self._viewers)

    async def broadcast(self, chunk): 
        if not self._viewers: 
            return 

        async with self._lock: 
            targets = list(self._viewers)

        dead = []
        for viewer in targets: 
            try: 
                await asyncio.wait_for(viewer.send_bytes(chunk), timeout=SEND_TIMEOUT)
            except (asyncio.TimeoutError, Exception):
                dead.append(viewer)

        for viewer in dead: 
            log.info("dropping slow video viewer")
            await self.remove_viewer(viewer)

video_hub = VideoHub()