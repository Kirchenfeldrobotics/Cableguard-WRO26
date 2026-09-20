import os 
import logging
from typing import Annotated

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import Field, ValidationError, TypeAdapter

from app.ws.hub import hub 
from app.database import session_scope
from app.repository.ingest import store
from app.auth import authenticate_robot, authenticate_ui
from comm_protocols.messages import MotionTelemetry, SpeedCmd, StopCmd
from app.auth import authenticate_robot
from comm_protocols.messages import Alive, Defect as DefectMsg, MotionTelemetry, SpeedCmd, StopCmd, VisionTelemetry
 
ROBOT_TOKEN = os.environ["CABLEGUARD_ROBOT_TOKEN"]

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ws")

# Every RobotMessage subclass the robot may send. Without Defect here the
# persist path in repository/ingest.py is unreachable.
FromRobot = TypeAdapter(
    Annotated[Alive | MotionTelemetry | DefectMsg | VisionTelemetry, Field(discriminator="type")]
)
FromUi   = TypeAdapter(Annotated[SpeedCmd | StopCmd, Field(discriminator="type")])

# Route where robot can subscribe to socket ans send messages to, which are broadcasted to ui clients or persisted (or both)
@router.websocket("/robot")
async def robot_link(sock: WebSocket): 
    if not await authenticate_robot(sock): 
        return 

    await sock.accept()
    await hub.attach_robot(sock)

    try: 
        async for raw in sock.iter_text(): 
            try: 
                msg = FromRobot.validate_json(raw)
            except ValidationError: 
                log.warning("bad robot message: %s", raw[:200])
                continue 

            if msg.persist: 
                try: 
                    with session_scope() as db: 
                        store(db, msg)
                except Exception: 
                    log.exception("failed to store: %s", msg.type)
            
            if msg.live: 
                await hub.broadcast(msg.model_dump())

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



