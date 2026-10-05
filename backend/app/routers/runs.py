from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Rope, Run, utcnow
from app.repository import state as state_repo
from app.schemas import RunCreate, RunOut

router = APIRouter(prefix="/api/runs", tags=["runs"])

# List all runs of a rope based on a rope id
@router.get("", response_model=list[RunOut])
def list_runs(rope_id: str | None = None, db: Session = Depends(get_db)): 
    q = db.query(Run)
    if rope_id is not None: 
        q = q.filter(Run.rope_id == rope_id)
    return q.order_by(Run.started_at.desc()).all()

# create a new run based on the RunCreate schema 
@router.post("", response_model=RunOut, status_code=201)
def create_run(payload: RunCreate, db: Session = Depends(get_db)): 
    if db.get(Rope, payload.rope_id) is None: 
        raise HTTPException(400, "rope not found")
    run = Run(**payload.model_dump())
    db.add(run)
    db.commit()
    db.refresh(run)
    return run 

# Close a run. Finishing is what makes it show up in the rope history and the trend,
# a run with no end is still being recorded into
@router.post("/{run_id}/finish", response_model=RunOut)
def finish_run(run_id: str, db: Session = Depends(get_db)): 
    run = db.get(Run, run_id)
    if run is None: 
        raise HTTPException(404, "run not found")
    if run.finished_at is None: 
        run.finished_at = utcnow()
        db.commit()
        db.refresh(run)
    return run 

# Delete a run based on a run:id
@router.delete("/{run_id}", status_code=204)
def delete_run(run_id: str, db: Session = Depends(get_db)): 
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(404, "run not found")
    # the robot is still recording into it, and the webapp still shows it as the live run
    if state_repo.get_state(db).current_run_id == run_id:
        raise HTTPException(409, "this run is being recorded, finish it first")
    db.delete(run)
    db.commit()
