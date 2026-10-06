import logging

from fastapi import APIRouter, HTTPException

from app.routers.ws import hub
from comm_protocols.messages import UpdateCmd

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/robot", tags=["robot"])


# Have the robot update itself: it pulls its software and restarts on it. This only hands
# the command over. That the update runs, what it failed on and the commit the robot ends
# up on are the robot's to report, in its motion telemetry
@router.post("/update", status_code=204)
async def update_robot():
    locked = hub.update_locked()
    if locked is not None:
        raise HTTPException(409, locked)

    if not await hub.to_robot(UpdateCmd().model_dump()):
        raise HTTPException(409, "the robot is offline")
    log.info("robot update requested")
