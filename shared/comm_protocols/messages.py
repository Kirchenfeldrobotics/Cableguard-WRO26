from typing import ClassVar, Literal 
from pydantic import BaseModel, Field 

from .settings import RobotSettings



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
    # both default to what a robot without the rope socket code does, so a server that is
    # ahead of the robot still reads its telemetry
    robot_open: bool = False    # camera ring parked clear of a rope socket, detector off
    socket_watch: bool = False  # the distance sensor may open the robot by itself
    settings_version: int = 0   # the settings the robot is actually running on, see SettingsCmd
    seq: int

# What the robot's distance sensor sees. Live only, a reading is worthless a second later
class DistanceTelemetry(RobotMessage):
    type: Literal["distance_telemetry"] = "distance_telemetry"
    live: ClassVar[bool]                = True
    distance_m: float | None    # to the nearest object, None when nothing is in the sensor's range
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

# Open the robot so it can pass a rope socket: the camera ring parks at an angle that clears
# the socket and the detector stops. What opened it decides what closes it again, so an
# opening the operator asked for ends with CloseCmd and nothing else
class OpenCmd(BaseModel):
    type: Literal["open"] = "open"

class CloseCmd(BaseModel):
    type: Literal["close"] = "close"

# Arm or disarm the distance sensor's own rope socket trigger
class SocketWatchCmd(BaseModel):
    type: Literal["socket_watch"] = "socket_watch"
    enabled: bool

# The operator's settings, the whole set of them at once. Sent when the robot connects and
# again on every change, so the robot never has to piece a configuration together. The
# version is the server's count of changes and comes straight back in the motion telemetry:
# that, not the command being accepted, is what says the robot is running on these values
class SettingsCmd(BaseModel):
    type: Literal["settings"] = "settings"
    version: int
    settings: RobotSettings