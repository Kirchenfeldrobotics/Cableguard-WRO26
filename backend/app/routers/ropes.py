from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Rope
from app.schemas import RopeCreate, RopeOut, RopeUpdate

router = APIRouter(prefix="/api/ropes", tags=["ropes"])

# return list of all ropes
@router.get("", response_model=list[RopeOut])
def list_ropes(db: Session = Depends(get_db)): 
    return db.query(Rope).order_by(Rope.name).all()

# Create a new rope (fields specified in schemas.py)
@router.post("", response_model=RopeOut, status_code=201)
def create_rope(payload: RopeCreate, db: Session = Depends(get_db)): 
    rope = Rope(**payload.model_dump())
    db.add(rope)
    try: 
        db.commit()
    except IntegrityError: 
        db.rollback()
        raise HTTPException(409, "a rope with that name already exists")
    db.refresh(rope)
    return rope

# Correct the length of a rope (fields specified in schemas.py)
@router.patch("/{rope_id}", response_model=RopeOut)
def update_rope(rope_id: str, payload: RopeUpdate, db: Session = Depends(get_db)):
    rope = db.get(Rope, rope_id)
    if rope is None:
        raise HTTPException(404, "rope not found")
    rope.length_m = payload.length_m
    db.commit()
    db.refresh(rope)
    return rope

# Delete rope based on id
@router.delete("/{rope_id}", status_code=204)
def delete_rope(rope_id: str, db: Session = Depends(get_db)): 
    rope = db.get(Rope, rope_id)
    if rope is None: 
        raise HTTPException(404, "rope not found")
    db.delete(rope)
    db.commit()
