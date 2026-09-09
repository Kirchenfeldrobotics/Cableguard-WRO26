from sqlalchemy import select 
from sqlalchemy.orm import Session 

from app.models import Defect 

def list_defects(db, run_id): 
    stmt = select(Defect)
    if run_id is not None: 
        stmt = stmt.where(Defect.run_id == run_id)
    return list(db.execute(stmt).scalars())

def get_defect(db, defect_id): 
    return db.get(Defect, defect_id)
