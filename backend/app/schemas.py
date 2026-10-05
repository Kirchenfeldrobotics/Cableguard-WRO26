from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from comm_protocols.settings import RobotSettings, SettingGroup, SettingInfo

# TODO: Create schemas for data that is persisted

# Credentials sent by the webapp login form
class LoginRequest(BaseModel): 
    username: str 
    password: str

# Key read from the NFC tag on the robot
class NfcLoginRequest(BaseModel):
    key: str

# Schema for the signed-in operator
class UserOut(BaseModel): 
    model_config = ConfigDict(from_attributes=True)

    id: str 
    username: str 

# Schema for the JWT handed to the webapp after a successful login
class TokenOut(BaseModel): 
    access_token: str 
    token_type: Literal["bearer"] = "bearer"

    # Seconds until the token expires
    expires_in: int 

    user: UserOut

# Length of a rope in metres. The webapp draws the rope to scale, so a slip of a few zeros
# too many is refused rather than drawn
RopeLength = Annotated[float, Field(gt=0, le=100_000)]

# Schema for the rope creation
class RopeCreate(BaseModel):
    name: str
    length_m: RopeLength

# Schema for a change to a rope. The length is the only thing about it that can be corrected
class RopeUpdate(BaseModel):
    length_m: RopeLength

# Schema for rope output
class RopeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    # Only empty for a rope that was created before the length was asked for
    length_m: float | None
    created_at: datetime

# Schema for run creation
class RunCreate(BaseModel): 
    name: str
    rope_id: str 

# Schema for run output
class RunOut(BaseModel): 
    model_config = ConfigDict(from_attributes=True)

    id: str 
    name: str 
    rope_id: str 
    started_at: datetime
    finished_at: datetime | None 

# Schema for current rope/run selection
class CurrentSelection(BaseModel): 
    rope_id: str | None 
    run_id: str | None 

# Schema for the robot settings page. The values are only half of it: the page also needs
# to know what every setting means and what it may be set to, and that is read off the
# settings model rather than repeated in the webapp
class SettingsOut(BaseModel): 
    version: int 
    updated_at: datetime
    values: RobotSettings
    fields: list[SettingInfo]
    groups: list[SettingGroup]

# Schema for a settings change. Only the settings named here move, the rest keep the value
# they have, so the page can send one field or all of them
class SettingsUpdate(BaseModel): 
    values: dict[str, float]

# Schema for defect output
class DefectOut(BaseModel): 
    model_config = ConfigDict(from_attributes=True)

    id: str 
    run_id: str 

    kind: Literal["lf", "lma"]

    pos_to_start: float

    created_at: datetime

    # Whether the operator has looked at it
    reviewed: bool

    # Only set when the vision model reported the defect
    label: str | None
    confidence: float | None
    cam: int | None
    box_x1: float | None
    box_y1: float | None
    box_x2: float | None
    box_y2: float | None
    # Set when the frame the defect was found in is stored, GET /api/defects/{id}/frame
    frame_id: str | None

# Schema for a review. One flaw on the rope arrives as several detections and the webapp is
# what groups them, so it names every detection the operator's decision covers
class DefectReview(BaseModel):
    defect_ids: list[str]
    reviewed: bool

# Schema for removing detections the operator flagged as a false positive
class DefectRemoval(BaseModel):
    defect_ids: list[str]