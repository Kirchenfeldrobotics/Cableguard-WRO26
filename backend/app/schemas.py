from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

# TODO: Create schemas for data that is persisted

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
    rope_id: str 

# Schema for run output
class RunOut(BaseModel): 
    model_config = ConfigDict(from_attributes=True)

    id: int 
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

    anchor_id: str 
    pos_to_anchor: float

    created_at: datetime