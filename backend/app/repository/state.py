from sqlalchemy.orm import Session

from app.models import AppState, RobotState

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

# the switches the robot is told again whenever it connects, written on first use
def get_robot_state(db):
    state = db.get(RobotState, 1)

    if state is None:
        state = RobotState(id=1)
        db.add(state)
        db.flush()

    return state

def get_video_stream(db):
    return get_robot_state(db).video_stream

def set_video_stream(db, enabled):
    get_robot_state(db).video_stream = enabled
