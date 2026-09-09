from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

def utcnow(): 
    return datetime.now(timezone.utc)

# Runs can be performed on a rope
class Rope(Base): 
    __tablename__ = "ropes"

    id: Mapped[str]                = mapped_column(primary_key=True)
    name: Mapped[str]              = mapped_column(String(120), unique=True)
    length_m: Mapped[float | None] = mapped_column(default=None)
    created_at: Mapped[datetime]   = mapped_column(default=utcnow)

    runs: Mapped[list["Run"]] = relationship(
        back_populates="rope", cascade="all, delete-orphan"
    )

# During a run anchors and defects are detected
class Run(Base): 
    __tablename__ = "runs"

    id: Mapped[str]                      = mapped_column(primary_key=True)
    rope_id: Mapped[str]                 = mapped_column(ForeignKey("ropes.id", ondelete="CASCADE"), index=True)
    started_at: Mapped[datetime]         = mapped_column(default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)

    rope: Mapped[Rope] = relationship(back_populates="runs")
    anchors: Mapped[list["Anchor"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )
    defects: Mapped[list["Defect"]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

# A anchor is known point on the rope, pos of defects are expressed relativ to one 
class Anchor(Base): 
    __tablename__ = "anchors"

    id: Mapped[str]                     = mapped_column(primary_key=True)
    run_id: Mapped[str]                 = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]                   = mapped_column(String(36))
    distance_to_origin_m: Mapped[float] = mapped_column()

    defects: Mapped[list["Defect"]] = relationship(
        back_populates="anchor", cascade="all, delete-orphan"
    )

# A rope defect 
class Defect(Base): 
    __tablename__ = "defects"

    id: Mapped[str]                     = mapped_column(primary_key=True)
    run_id: Mapped[str]                 = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str]                   = mapped_column(String(8))
    anchor_id: Mapped[str]              = mapped_column(ForeignKey("anchors.id", ondelete="CASCADE"), index=True)
    distance_to_anchor_m: Mapped[float] = mapped_column()

class AppState(Base): 
    __tablename__ = "app_state"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    current_rope_id: Mapped[str | None] = mapped_column(ForeignKey("ropes.id", ondelete="SET NULL"), default=None)
    current_run_id: Mapped[str | None]  = mapped_column(ForeignKey("runs.id", ondelete="SET NULL"), default=None)