from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.repository import state as state_repo
from app.models import Run
from app.routers.ws import hub
from app.schemas import CurrentSelection

router = APIRouter(prefix="/api/current", tags=["current"])

# Read the current rope/run 
@router.get("", response_model=CurrentSelection)
def get_current(db=Depends(get_db)): 
    state = state_repo.get_state(db)
    db.commit()
    return CurrentSelection(rope_id=state.current_rope_id, run_id=state.current_run_id)

# Set current rope/run 
@router.post("", response_model=CurrentSelection)
async def set_current(payload, db=Depends(get_db)): 
    if payload.run_id is not None: 
        run = db.get(Run, payload.run_id)
        if run is None: 
            raise HTTPException(400, "run not found")
        if payload.rope_id is not None and run.rope_id != payload.rope_id: 
            raise HTTPException(400, "run does not belong to that rope")
        payload.rope_id = run.rope_id

    state_repo.set_current(db, payload.rope_id, payload.run_id)
    db.commit()

    await hub.broadcast({
        "type": "current_changed", 
        "run_id": payload.rope_id, 
        "rope_id": payload.run_id
    })

    return payload