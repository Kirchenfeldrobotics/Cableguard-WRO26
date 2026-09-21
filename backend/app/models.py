import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import ForeignKey, LargeBinary, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

def utcnow(): 
    return datetime.now(timezone.utc)

def new_id(): 
    return uuid.uuid4().hex

# Operator account that may sign in to the webapp
class User(Base): 
    __tablename__ = "users"

    id: Mapped[str]              = mapped_column(primary_key=True, default=new_id)
    username: Mapped[str]        = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str]   = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=utcnow)
# Primary keys are generated here: the *Create schemas never carry an id
def new_id(): 
    return str(uuid.uuid4())

# Runs can be performed on a rope
class Rope(Base): 
    __tablename__ = "ropes"

    id: Mapped[str]                = mapped_column(primary_key=True, default=new_id)
    name: Mapped[str]              = mapped_column(String(120), unique=True)
    length_m: Mapped[float | None] = mapped_column(default=None)
    created_at: Mapped[datetime]   = mapped_column(default=utcnow)

    runs: Mapped[list["Run"]] = relationship(
        back_populates="rope", cascade="all, delete-orphan"
    )

# During a run defects are detected
class Run(Base): 
    __tablename__ = "runs"

    id: Mapped[str]                      = mapped_column(primary_key=True, default=new_id)
    name: Mapped[str]                    = mapped_column(String(120))
    rope_id: Mapped[str]                 = mapped_column(ForeignKey("ropes.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime]         = mapped_column(default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)

    rope: Mapped[Rope] = relationship(back_populates="runs")
    defects: Mapped[list["Defect"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

# The camera frame a detection was made in. Stored once and shared by every defect found in
# it, the boxes of those defects are normalised to it
class Frame(Base): 
    __tablename__ = "frames"

    id: Mapped[str]              = mapped_column(primary_key=True, default=new_id)
    run_id: Mapped[str]          = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    cam: Mapped[int]             = mapped_column()
    jpeg: Mapped[bytes]          = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

# A rope defect 
class Defect(Base): 
    __tablename__ = "defects"

    id: Mapped[str]                     = mapped_column(primary_key=True, default=new_id)
    run_id: Mapped[str]                 = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str]                   = mapped_column(String(8))
    pos_to_start: Mapped[float]         = mapped_column()
    created_at: Mapped[datetime]        = mapped_column(default=utcnow)

    # What the vision model saw. A defect reported by another sensor carries none of it,
    # the box is normalised to the frame it was found in
    label: Mapped[str | None]           = mapped_column(String(64), default=None)
    confidence: Mapped[float | None]    = mapped_column(default=None)
    cam: Mapped[int | None]             = mapped_column(default=None)
    box_x1: Mapped[float | None]        = mapped_column(default=None)
    box_y1: Mapped[float | None]        = mapped_column(default=None)
    box_x2: Mapped[float | None]        = mapped_column(default=None)
    box_y2: Mapped[float | None]        = mapped_column(default=None)
    frame_id: Mapped[str | None]        = mapped_column(ForeignKey("frames.id", ondelete="SET NULL"), default=None)

    run: Mapped["Run"] = relationship(back_populates="defects")
    # without it the frame and its defects are flushed in any order and the foreign key fails
    frame: Mapped["Frame | None"] = relationship()

class AppState(Base): 
    __tablename__ = "app_state"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    current_rope_id: Mapped[str | None] = mapped_column(ForeignKey("ropes.id", ondelete="SET NULL"), default=None)
    current_run_id: Mapped[str | None]  = mapped_column(ForeignKey("runs.id", ondelete="SET NULL"), default=None)