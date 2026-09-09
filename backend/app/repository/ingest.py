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

    # TODO: distance to start
    db.add(Defect(
        id=str(uuid.uuid4()), 
        run_id=current_ids["current_run_id"], 
        kind=msg.kind, 
        distance_to_start_m=0.0
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