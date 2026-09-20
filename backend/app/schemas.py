from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

# TODO: Create schemas for data that is persisted

# Credentials sent by the webapp login form
class LoginRequest(BaseModel): 
    username: str 
    password: str 

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

# Schema for the rope creation
class RopeCreate(BaseModel): 
    name: str 

# Schema for rope output
class RopeOut(BaseModel): 
    model_config = ConfigDict(from_attributes=True)

    id: str 
    name: str 
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

# Schema for defect output
class DefectOut(BaseModel): 
    model_config = ConfigDict(from_attributes=True)

    id: str 
    run_id: str 

    kind: Literal["lf", "lma"]

    pos_to_start: float

    created_at: datetime

    # Only set when the vision model reported the defect
    label: str | None
    confidence: float | None
    cam: int | None
    box_x1: float | None
    box_y1: float | None
    box_x2: float | None
    box_y2: float | None