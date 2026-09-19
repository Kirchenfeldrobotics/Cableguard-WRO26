import asyncio 
import websockets
import logging
import os

log = logging.getLogger(__name__)

URL   = os.environ["CABLEGUARD_VID_WS_URL"]
TOKEN = os.environ["CABLEGUARD_ROBOT_TOKEN"]

# always holds the latest frame, discards old one
class LatestFrame: 
    def __init__(self): 
        self._frame = None 
        self._event = asyncio.Event()

    def put(self, data: bytes): 
        self._frame = data 
        self._event.set()

    async def get(self): 
        await self._event.wait()
        self._event.clear()
        return self._frame

class VideoLink: 
    def __init__(self, fps=8): 
        self._period = 1.0/fps
        self.buffers = {0: LatestFrame(), 1: LatestFrame()}

    # add jpeg to the buffer 
    def submit(self, cam_idx: int, jpeg: bytes): 
        self.buffers[cam_idx].put(jpeg)

    # starts task that streams videos
    async def run(self): 
        async for sock in websockets.connect(URL, additional_headers={"Authorization": f"Bearer {TOKEN}"}, ping_interval=20): 
            try: 
                async with asyncio.TaskGroup() as tg: 
                    for idx in self.buffers: 
                        tg.create_task(self._pump(sock, idx))
            except* websockets.ConnectionClosed: 
                log.info("video link closed, reconnecting...")

    # steams the two videos
    async def _pump(self, sock, idx: int): 
        while True: 
            jpeg = await self.buffers[idx].get()
            await sock.send(bytes([idx]) + jpeg)
            await asyncio.sleep(self._period)