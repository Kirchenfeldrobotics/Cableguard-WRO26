import asyncio 
import json 
import os 
import logging
from typing import Annotated

import websockets
from pydantic import Field, TypeAdapter, ValidationError

from .outbox import Outbox
from comm_protocols.messages import CloseCmd, OpenCmd, ResetOriginCmd, SocketWatchCmd, StartCmd, StopCmd

log = logging.getLogger(__name__)

URL   = os.environ["CABLEGUARD_WS_URL"]
TOKEN = os.environ["CABLEGUARD_ROBOT_TOKEN"]

FromServer = TypeAdapter(
    Annotated[
        StartCmd | StopCmd | ResetOriginCmd | OpenCmd | CloseCmd | SocketWatchCmd,
        Field(discriminator="type"),
    ]
)

class RobotLink: 
    def __init__(self, outbox, heartbeat_s=5.0, send_hz=5.0): 
        self.outbox       = outbox
        self.send_hz      = send_hz
        self._heartbeat_s = heartbeat_s
        self._sock        = None 
        self._on_command  = None 

    # register a callback handler, that recieves the data from the ui clients
    def on_command(self, handler): 
        self._on_command = handler

    # queue a message 
    def send(self, msg: dict): 
        self.outbox.add_msg(msg)

    # send a live message
    async def send_live(self, msg: dict):
        sock = self._sock
        if sock is None:
            return False
        try:
            await sock.send(json.dumps(msg))
            return True
        except websockets.ConnectionClosed:
            return False

    # return whether or not the link is connected 
    @property
    def connected(self): 
        return self._sock is not None 

    # keeps reconnecting to the socket and creates tasks 
    async def run(self): 
        async for sock in websockets.connect(
            URL, 
            additional_headers={"Authorization": f"Bearer {TOKEN}"},
            ping_interval=10,
            ping_timeout=20,
            open_timeout=10,
            max_size=2**20,
        ): 
            log.info("link established")
            self._sock = sock 
            try: 
                async with asyncio.TaskGroup() as tg: 
                    tg.create_task(self._heartbeat_loop(sock))
                    tg.create_task(self._send_loop(sock))
                    tg.create_task(self._receive_loop(sock))
            except* websockets.ConnectionClosed: 
                log.warning("link closed, reconnecting")
            finally: 
                self._sock = None 
                log.info("link down")

    # keeps sending alive packages to the socket
    async def _heartbeat_loop(self, sock): 
        while True: 
            await sock.send(json.dumps({"type": "alive"}))
            await asyncio.sleep(self._heartbeat_s)

    # keeps sending pending messages to the socket
    async def _send_loop(self, sock): 
        while True: 
            batch = self.outbox.pending()
            for msg in batch: 
                await sock.send(json.dumps(msg)) 
            if batch: 
                self.outbox.mark_sent(len(batch))
            await asyncio.sleep(1.0/self.send_hz)

    # receives messages from the socket, validates them and hands them over to the cmd handler
    async def _receive_loop(self, sock): 
        async for raw in sock: 
            try: 
                cmd = FromServer.validate_json(raw)
            except ValidationError: 
                log.warning("rejected message: %s", raw[:200])
                continue 
            if self._on_command is not None: 
                self._on_command(cmd)
