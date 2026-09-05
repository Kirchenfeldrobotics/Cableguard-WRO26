from typing import ClassVar, Literal 
from pydantic import BaseModel, fIELD 



# == Robot ---> API ==

# Parent class to every robot message
class RobotMessage(BaseModel):
    live: ClassVar[bool]    = False      
    persist: ClassVar[bool] = False

# Status robot 
class Alive(RobotMessage): 
    type: Literal["alive"] = "alive"
    live: ClassVar[bool]   = True 

# Robots state of motion 
class MotionTelemetry(RobotMessage): 
    type: Literal["motion_telemetry"] = "motion_telemetry"
    live: ClassVar[bool]              = True 
    speed: float 
    microsteps: int 
    seq: int 

# Robots position  
class Defect(RobotMessage): 
    type: Literal["defect"] = "defect"
    persist: ClassVar[bool] = True 
    kind: Literal["lf", "lma"]
    distance_from_origin: float
    seq: int 

# == API ---> Robot ==

# Speed instruction 
class SpeedCmd(BaseModel): 
    type: Literal["speed"] = "speed"
    value: float

class StopCmd(BaseModel): 
    type: Literal["stop"] = "stop"