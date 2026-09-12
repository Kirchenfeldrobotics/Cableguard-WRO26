from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Rope, Run
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

# Delete a run based on a run:id
@router.delete("/{run_id}", status_code=204)
def delete_run(run_id: str, db: Session = Depends(get_db)): 
    run = db.get(Run, run_id)
    if run is None: 
        raise HTTPException(404, "run not found")
    db.delete(run)
    db.commit()
