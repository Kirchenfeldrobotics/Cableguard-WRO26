import logging
from collections.abc import Callable
import uuid

from sqlalchemy.orm import Session
from comm_protocols.messages import Defect as DefectMsg

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

# Mapping from message type to handler 
_HANDLERS = {
    DefectMsg: _store_defect, 
} 

# presist robot message according to handler function (based on msg type)
def store(db, msg): 
    handler = _HANDLERS.get(type(msg))
    if handler is None: 
        log.error("no state handler for %s", type(msg).__name__)
        return 
    handler(db, msg)