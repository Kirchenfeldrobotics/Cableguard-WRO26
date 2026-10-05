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

# The defects behind these ids. One that is gone already is left out rather than refused:
# another browser may have removed it in the meantime
def _by_ids(db, defect_ids):
    return list(db.execute(select(Defect).where(Defect.id.in_(defect_ids))).scalars())

# Mark defects as looked at, or take the mark back
def set_reviewed(db, defect_ids, reviewed):
    defects = _by_ids(db, defect_ids)
    for defect in defects:
        defect.reviewed = reviewed
    return defects

# Delete defects for good, and with them every frame none of the remaining ones was found in
def delete_defects(db, defect_ids):
    defects   = _by_ids(db, defect_ids)
    frame_ids = {defect.frame_id for defect in defects if defect.frame_id is not None}

    for defect in defects:
        db.delete(defect)
    db.flush()

    for frame_id in frame_ids:
        still_used = db.execute(select(Defect.id).where(Defect.frame_id == frame_id).limit(1)).first()
        if still_used is None:
            db.delete(db.get(Frame, frame_id))

# JPEG of the frame a defect was found in, None when none was stored
def get_frame(db, defect_id): 
    defect = db.get(Defect, defect_id)
    if defect is None or defect.frame_id is None: 
        return None
    frame = db.get(Frame, defect.frame_id)
    return frame.jpeg if frame is not None else None
