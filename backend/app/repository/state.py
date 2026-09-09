from sqlalchemy.orm import Session

from app.models import AppState

def get_state(db): 
    state = db.get(AppState, 1)

    if state is None: 
        state = AppState(id=1)
        db.add(state)
        db.flush()

    return state

def set_current(db, rope_id, run_id): 
    state                 = get_state(db)
    state.current_rope_id = rope_id
    state.current_run_id  = run_id
    return state 

def get_current(db): 
    state = get_state(db)
    return {"current_rope_id": state.current_rope_id, "current_run_id": state.current_run_id} 
