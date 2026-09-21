from typing import ClassVar, Literal 
from pydantic import BaseModel, Field 



# lf = local fault (broken wires), lma = loss of metallic area (corrosion and wear)
DefectKind = Literal["lf", "lma"]

# == Robot ---> API ==

# Parent class to every robot message
class RobotMessage(BaseModel):
    live: ClassVar[bool]    = False      
    persist: ClassVar[bool] = False

# Status robot 
class Alive(RobotMessage): 
    type: Literal["alive"] = "alive"
    live: ClassVar[bool]   = True 

# Robots state of motion. The robot owns the drive geometry, so it reports both the exact
# step counts and the metres they work out to, nobody downstream needs the conversion
class MotionTelemetry(RobotMessage): 
    type: Literal["motion_telemetry"] = "motion_telemetry"
    live: ClassVar[bool]              = True 
    speed: float                # microsteps per second, signed with the drive direction
    speed_mps: float            # the same speed in metres per second
    microsteps: int             # since the origin was last reset
    metres: float               # the same position in metres
    scan_speed_mps: float       # what the scan plan asks the drive to hold while running
    detect_fps: float           # detector cycles per second the plan is built for
    seq: int 

# Robots position  
class Defect(RobotMessage): 
    type: Literal["defect"] = "defect"
    persist: ClassVar[bool] = True 
    kind: DefectKind
    distance_from_origin: float
    seq: int 

# One box the detector found, normalised to the frame it was found in
class VisionDetection(BaseModel): 
    label: str                                  # class name as the model reports it
    kind: DefectKind | None = None              # None as long as the label is not mapped
    confidence: float = Field(ge=0.0, le=1.0)
    box: tuple[float, float, float, float]      # x1, y1, x2, y2, 0..1

# What one camera saw in one frame, empty detections included
class VisionTelemetry(RobotMessage): 
    type: Literal["vision_telemetry"] = "vision_telemetry"
    live: ClassVar[bool]              = True 
    persist: ClassVar[bool]           = True 
    seq: int 
    cam: Literal[0, 1]
    captured_at: float                          # epoch seconds, a datetime would not survive json.dumps
    inference_ms: float 
    microsteps: int 
    distance_from_origin: float | None = None   # metres since the step counter was last reset
    frame_w: int 
    frame_h: int 
    detections: list[VisionDetection]
    jpeg: str | None = None                     # base64 JPEG of the frame, only sent with detections

# == API ---> Robot ==

# Start scanning. Only the direction is ours to pick, the robot derives the speed from how
# fast its detector runs so that the frames cover the rope end to end
class StartCmd(BaseModel): 
    type: Literal["start"] = "start"
    direction: Literal["forward", "reverse"] = "forward"

class StopCmd(BaseModel): 
    type: Literal["stop"] = "stop"

# A run is measured from where the robot sits when the run is selected
class ResetOriginCmd(BaseModel): 
    type: Literal["reset_origin"] = "reset_origin"