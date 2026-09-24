import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.repository import settings as settings_repo
from app.routers.ws import hub
from app.schemas import SettingsOut, SettingsUpdate
from comm_protocols.messages import SettingsCmd
from comm_protocols.settings import RobotSettings, describe_groups, describe_settings

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])


# The stored values plus what the settings page needs to draw a row for each of them, read
# off the settings model rather than repeated in the webapp
def _out(row, values: RobotSettings) -> SettingsOut:
    return SettingsOut(version=row.version, updated_at=row.updated_at, values=values,
                       fields=describe_settings(), groups=describe_groups())


# "headroom: Input should be less than or equal to 5", as the operator sees it
def _readable(exc: ValidationError) -> str:
    return "; ".join(f"{error['loc'][0]}: {error['msg']}" for error in exc.errors())


# Hand the new set to the robot and tell every open browser about it. A robot that is
# offline is not an error: it is given the current set the moment it connects, see
# routers/ws.py
async def _publish(version: int, values: RobotSettings) -> None:
    if not await hub.to_robot(SettingsCmd(version=version, settings=values).model_dump()):
        log.warning("settings version %d stored while the robot is offline, it gets them on connect",
                    version)
    await hub.broadcast({"type": "settings_changed", "version": version})


@router.get("", response_model=SettingsOut)
def read_settings(db: Session = Depends(get_db)):
    row = settings_repo.get_row(db)
    out = _out(row, settings_repo.settings_of(row))
    db.commit()
    return out


# Change settings. Only the ones named in the body move; the robot is sent the whole new
# set, because it configures itself from all of it at once
@router.put("", response_model=SettingsOut)
async def write_settings(payload: SettingsUpdate, db: Session = Depends(get_db)):
    unknown = sorted(set(payload.values) - set(RobotSettings.model_fields))
    if unknown:
        raise HTTPException(422, f"no such setting: {', '.join(unknown)}")

    locked = hub.settings_locked()
    if locked is not None:
        raise HTTPException(409, locked)

    try:
        row, values = settings_repo.update_settings(db, payload.values)
    except ValidationError as exc:
        db.rollback()
        raise HTTPException(422, _readable(exc))

    out = _out(row, values)
    db.commit()

    await _publish(out.version, values)
    log.info("settings version %d: %s", out.version, ", ".join(sorted(payload.values)))
    return out


# Back to the constants the robot is built with
@router.post("/reset", response_model=SettingsOut)
async def reset_settings(db: Session = Depends(get_db)):
    locked = hub.settings_locked()
    if locked is not None:
        raise HTTPException(409, locked)

    row, values = settings_repo.reset_settings(db)
    out = _out(row, values)
    db.commit()

    await _publish(out.version, values)
    log.info("settings reset to the robot's defaults, version %d", out.version)
    return out
