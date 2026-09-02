import hmac, os 
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError, TypeAdapter

from app.ws.hub import hub 
from app.ws.protocols import MotionTelemetry, PositionTelemetry, SpeedCmd, StopCmd

ROBOT_TOKEN = os.environ("CABLEGUARD_ROBOT_TOKEN")

log = logging.getLogger(__name__)
router = APIRouter("/api/ws")

FromRobot = TypeAdapter(MotionTelemetry | PositionTelemetry)
FromUi   = TypeAdapter(SpeedCmd | StopCmd)

async def authenticate_robot(sock: WebSocket): 
    header = sock.headers.get("authorization", "")
    token  = header.removeprefix("Bearer ").strip()
    if not hmac.compare_digest(token, ROBOT_TOKEN): 
        await sock.close(code=status.WS_1008_POLICY_VIOLATION)
        return False 
    return True

# Route where robot can subscribe to socket and send messages to ui clients
@router.websocket("/robot")
async def robot_link(sock): 
    if not await authenticate_robot(sock): 
        return 

    await sock.accept()
    await hub.attach_robot(sock)

    try: 
        async for raw in sock.iter_text(): 
            try: 
                msg = FromRobot.validate_json(msg)
            except ValidationError: 
                log.warning("bad robot message: %s", raw[:200])
                continue 

            await hub.broadcast(msg.model_dump())

    except WebSocketDisconnect: 
        pass
    finally: 
        await hub.detach_robot(sock)

# Route where ui client can subscribe to soket and send messages to robot 
@router.websocket("/ui")
async def ui_link(sock): 
    await sock.accept()
    await hub.add_ui(sock)
    try:
        async for raw in sock.iter_text():
            try: 
                cmd = FromUi.validate_json(raw)
            except ValidationError: 
                await sock.send_json({"type": "error", "detail": "invalid command"})
                continue 

            if not await hub.to_robot(cmd.model_dump()): 
                await sock.send_json({"type": "error", "detail": "robot offline "})

    except WebSocketDisconnect: 
        pass
    finally:
        hub.remove_ui(sock)



