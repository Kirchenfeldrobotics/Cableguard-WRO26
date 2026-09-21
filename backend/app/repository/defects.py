from sqlalchemy import select 
from sqlalchemy.orm import Session 

from app.models import Defect, Frame 

def list_defects(db, run_id): 
    stmt = select(Defect)
    if run_id is not None: 
        stmt = stmt.where(Defect.run_id == run_id)
    return list(db.execute(stmt).scalars())

def get_defect(db, defect_id): 
    return db.get(Defect, defect_id)

# JPEG of the frame a defect was found in, None when none was stored
def get_frame(db, defect_id): 
    defect = db.get(Defect, defect_id)
    if defect is None or defect.frame_id is None: 
        return None
    frame = db.get(Frame, defect.frame_id)
    return frame.jpeg if frame is not None else None
