from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session 

from app.database import get_db 
from app.repository import defects as repo 
from app.schemas import DefectOut

router = APIRouter(prefix="/api/defects", tags=["defects"])

@router.get("", response_model=list[DefectOut])
def list_defects(run_id: str | None = None, db: Session = Depends(get_db)): 
    return repo.list_defects(db, run_id)

@router.get("/{defect_id}", response_model=DefectOut)
def get_defect(defect_id: str, db: Session = Depends(get_db)): 
    defect = repo.get_defect(db, defect_id)
    if defect is None: 
        raise HTTPException(404, "defect not found")
    return defect

# The frame the defect was found in, as the robot's camera saw it
@router.get("/{defect_id}/frame")
def get_defect_frame(defect_id: str, db: Session = Depends(get_db)): 
    jpeg = repo.get_frame(db, defect_id)
    if jpeg is None: 
        raise HTTPException(404, "no frame stored for this defect")
    return Response(content=jpeg, media_type="image/jpeg")