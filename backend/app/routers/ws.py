import os 
import logging
from typing import Annotated

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import Field, ValidationError, TypeAdapter

from app.ws.hub import hub 
from app.database import session_scope
from app.repository.ingest import store
from app.repository import settings as settings_repo
from app.auth import authenticate_robot, authenticate_ui
from comm_protocols.messages import (
    Alive,
    CloseCmd,
    Defect as DefectMsg,
    DistanceTelemetry,
    MotionTelemetry,
    OpenCmd,
    SettingsCmd,
    SocketWatchCmd,
    StartCmd,
    StopCmd,
    VisionTelemetry,
)
 
ROBOT_TOKEN = os.environ["CABLEGUARD_ROBOT_TOKEN"]

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ws")

# Every RobotMessage subclass the robot may send. Without Defect here the
# persist path in repository/ingest.py is unreachable.
FromRobot = TypeAdapter(
    Annotated[
        Alive | MotionTelemetry | DistanceTelemetry | DefectMsg | VisionTelemetry,
        Field(discriminator="type"),
    ]
)
# The robot picks its own speed, the operator only starts, stops and sets the direction, and
# opens the robot to let it pass a rope socket
FromUi   = TypeAdapter(
    Annotated[
        StartCmd | StopCmd | OpenCmd | CloseCmd | SocketWatchCmd,
        Field(discriminator="type"),
    ]
)

# The robot boots on the constants it is built with, so the operator's settings are the
# first thing it is told. It reports the version back in its motion telemetry once they are
# really in force, which is what the settings page reads
async def send_settings(): 
    with session_scope() as db: 
        row = settings_repo.get_row(db)
        cmd = SettingsCmd(version=row.version, settings=settings_repo.settings_of(row))
    await hub.to_robot(cmd.model_dump())

# Route where robot can subscribe to socket ans send messages to, which are broadcasted to ui clients or persisted (or both)
@router.websocket("/robot")
async def robot_link(sock: WebSocket): 
    if not await authenticate_robot(sock): 
        return 

    await sock.accept()
    await hub.attach_robot(sock)
    await send_settings()

    try: 
        async for raw in sock.iter_text(): 
            try: 
                msg = FromRobot.validate_json(raw)
            except ValidationError: 
                log.warning("bad robot message: %s", raw[:200])
                continue 

            if isinstance(msg, MotionTelemetry): 
                # the settings route refuses a change to a robot that is driving
                hub.note_motion(msg.speed)

            if msg.persist: 
                try: 
                    with session_scope() as db: 
                        store(db, msg)
                except Exception: 
                    log.exception("failed to store: %s", msg.type)
            
            # frames go to the database, not to every open browser at the detector's rate
            if msg.live: 
                await hub.broadcast(msg.model_dump(exclude={"jpeg"}))

    except WebSocketDisconnect: 
        pass
    finally: 
        await hub.detach_robot(sock)

# Route where ui client can subscribe to soket and send messages to robot 
@router.websocket("/ui")
async def ui_link(sock: WebSocket): 
    if not await authenticate_ui(sock): 
        return 

    await sock.accept()
    try:
        await hub.add_ui(sock)
        async for raw in sock.iter_text():
            try: 
                cmd = FromUi.validate_json(raw)
            except ValidationError: 
                await sock.send_json({"type": "error", "detail": "invalid command"})
                continue 

            if not await hub.to_robot(cmd.model_dump()): 
                await sock.send_json({"type": "error", "detail": "robot offline"})

    except WebSocketDisconnect: 
        pass
    finally:
        await hub.remove_ui(sock)



