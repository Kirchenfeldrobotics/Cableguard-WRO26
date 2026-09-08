from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Rope
from app.schemas import RopeCreate, RopeOut

router = APIRouter(prefix="/api/ropes", tags=["ropes"])

# return list of all ropes
@router.get("", response_model=list[RopeOut])
def list_ropes(db=Depends(get_db)): 
    return db.query(Rope).order_by(Rope.name).all()

# Create a new rope (fields specified in schemas.py)
@router.post("", response_model=RopeCreate, status_code=201)
def create_rope(payload, db=Depends(get_db)): 
    rope = Rope(**payload.model_dump())
    db.add(rope)
    db.commit()
    db.refresh(rope)
    return rope

# Delete rope based on id
@router.delete("/{rope_id}", status_code=204)
def delete_rope(rope_id, db=Depends(get_db)): 
    rope = db.get(Rope, rope_id)
    if rope is None: 
        raise HTTPException(404, "rope not found")
    db.delete(rope)
    db.commit()