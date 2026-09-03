from typing import Literal 
from pydantic import BaseModel 

# == Robot ---> API ==

# Robots state of motion 
class MotionTelemetry(BaseModel): 
    type: Literal["motion_telemetry"] = "motion_telemetry"
    speed: float 
    microsteps: int 
    seq: int 

# Robots position  
class PositionTelemetry(BaseModel): 
    type: Literal["position_telemetry"] = "position_telemetry"
    # TODO: type of finding (defect or wire mark), pos to next mark

# == API ---> Robot ==

# Speed instruction 
class SpeedCmd(BaseModel): 
    type: Literal["speed"] = "speed"
    value: float

class StopCmd(BaseModel): 
    type: Literal["stop"] = "stop"