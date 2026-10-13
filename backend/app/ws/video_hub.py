import asyncio
import logging 

from fastapi import WebSocket 

from app.ws.hub import hub
from comm_protocols.messages import VideoViewersCmd

log = logging.getLogger(__name__)

SEND_TIMEOUT = 0.1 

class VideoHub: 
    def __init__(self): 
        self._viewers      = set()
        self._lock         = asyncio.Lock()
        self._telling      = asyncio.Lock()   # one report to the robot at a time, see tell_robot

    # The robot only streams while somebody watches, so it hears of the first viewer to
    # come and of the last one to go. The ones in between change nothing for it
    async def add_viewer(self, sock): 
        async with self._lock: 
            first = not self._viewers
            self._viewers.add(sock)
        if first:
            await self.tell_robot()

    async def remove_viewer(self, sock): 
        async with self._lock: 
            watched = bool(self._viewers)
            self._viewers.discard(sock)
            last = watched and not self._viewers
        if last:
            await self.tell_robot()

    # Tell the robot whether anyone is watching. Whether they are is read here, under the
    # lock and right before it is sent, and not by the caller: two changes close together
    # would otherwise be free to arrive in the wrong order and leave the robot on the older
    # one. A robot that is offline misses this and is told when it connects
    async def tell_robot(self):
        async with self._telling:
            await hub.to_robot(VideoViewersCmd(watching=bool(self._viewers)).model_dump())

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
            try:
                await asyncio.wait_for(viewer.close(), timeout=SEND_TIMEOUT)
            except Exception:
                pass

video_hub = VideoHub()