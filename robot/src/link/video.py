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
    # The rate is the frame producer's, it is the only thing that fills the buffers and it
    # paces itself off the operator's stream setting. A pump waits on its buffer, so it can
    # never run ahead of that
    def __init__(self): 
        self.buffers = {0: LatestFrame(), 1: LatestFrame()}

        # The stream is the robot's largest upload and its mobile link is metered, so it only
        # runs while the operator has it switched on and somebody has the live view open.
        # Both start as what a robot did before it could be told either, streaming: the
        # server says how things really stand as soon as the control link is up
        self.enabled = True     # the operator's switch
        self.watched = True     # a browser has the live view open, as the server counts them

    # whether frames are wanted at all. The frame producer reads no camera while they are not
    @property
    def streaming(self):
        return self.enabled and self.watched

    # the operator's switch
    def set_enabled(self, enabled: bool):
        self._set(enabled, self.watched)

    # the server's count of viewers, as one bit
    def set_watched(self, watched: bool):
        self._set(self.enabled, watched)

    def _set(self, enabled, watched):
        was = self.streaming
        self.enabled = enabled
        self.watched = watched

        if self.streaming == was:
            return
        if self.streaming:
            log.info("live stream running")
        else:
            log.info("live stream paused, %s", "nobody is watching" if enabled else "switched off")

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
                    tg.create_task(self._watch(sock))
            except* websockets.ConnectionClosed: 
                log.info("video link closed, reconnecting...")

    # steams the two videos
    async def _pump(self, sock, idx: int): 
        while True: 
            jpeg = await self.buffers[idx].get()
            await sock.send(bytes([idx]) + jpeg)

    # A paused stream sends nothing, and a pump only finds a dead socket when it sends. The
    # next viewer would wait out a reconnect before the first frame, so the socket is read
    # as well: the server never sends on it, and reading raises the moment it closes
    async def _watch(self, sock):
        while True:
            await sock.recv()