import logging
from collections.abc import Callable
import uuid

from sqlalchemy.orm import Session
from comm_protocols.messages import Defect as DefectMsg, VisionTelemetry

from app.models import Defect 
from app.repository.state import get_current

log = logging.getLogger(__name__)

def _store_defect(db, msg): 
    current_ids = get_current(db)
    run_id      = current_ids["current_run_id"]

    # Defects belong to a run: with nothing selected there is nowhere to put
    # them, so drop the message instead of failing the NOT NULL constraint.
    if run_id is None: 
        log.warning("dropping %s: no run is selected", msg.type)
        return 

    db.add(Defect(
        id=str(uuid.uuid4()), 
        run_id=run_id, 
        kind=msg.kind, 
        pos_to_start=msg.distance_from_origin
    ))

# One row per detection. The robot reports every frame, also the empty ones, so that the
# link stays observable when nothing is found, but only detections belong in the table.
def _store_vision(db, msg): 
    if not msg.detections: 
        return 

    current_ids = get_current(db)
    run_id      = current_ids["current_run_id"]

    if run_id is None: 
        log.warning("dropping %s: no run is selected", msg.type)
        return 

    # pos_to_start is NOT NULL and there is nothing to fall back to
    if msg.distance_from_origin is None: 
        log.warning("dropping %s: the robot reports no position", msg.type)
        return 

    for det in msg.detections: 
        # the robot could not map the class name, writing a kind here would invent one
        if det.kind is None: 
            log.warning("skipping detection: %s is not mapped to a kind", det.label)
            continue 

        db.add(Defect(
            id=str(uuid.uuid4()), 
            run_id=run_id, 
            kind=det.kind, 
            pos_to_start=msg.distance_from_origin, 
            label=det.label, 
            confidence=det.confidence, 
            cam=msg.cam, 
            box_x1=det.box[0], 
            box_y1=det.box[1], 
            box_x2=det.box[2], 
            box_y2=det.box[3], 
        ))

# Mapping from message type to handler 
_HANDLERS = {
    DefectMsg: _store_defect, 
    VisionTelemetry: _store_vision, 
} 

# presist robot message according to handler function (based on msg type)
def store(db, msg): 
    handler = _HANDLERS.get(type(msg))
    if handler is None: 
        log.error("no state handler for %s", type(msg).__name__)
        return 
    handler(db, msg)