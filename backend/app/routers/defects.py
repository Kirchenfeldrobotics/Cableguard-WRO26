from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session 

from app.database import get_db 
from app.repository import defects as repo 
from app.schemas import DefectOut

router = APIRouter(prefix="/api/defects", tags=["defects"])

@router.get("", response_model=list[DefectOut])
def list_defects(run_id, db=Depends(get_db)): 
    return repo.list_defects(db, run_id)

@router.get("/{defect_id}", response_model=DefectOut)
def get_defect(defect_id, db=Depends(get_db)): 
    defect = repo.get_defect(db)
    if defect is None: 
        raise HTTPException(404, "defect not found")
    return defect