import logging

from pydantic import ValidationError

from app.models import RobotSettingsRow
from comm_protocols.settings import RobotSettings

log = logging.getLogger(__name__)


# The stored row, written with the robot's own defaults the first time anyone asks for it.
# Version 1 from the start, so it never matches the 0 a robot reports before it has been
# told anything
def get_row(db) -> RobotSettingsRow:
    row = db.get(RobotSettingsRow, 1)

    if row is None:
        row = RobotSettingsRow(id=1, version=1, values=RobotSettings().model_dump())
        db.add(row)
        db.flush()

    return row


# What a stored blob means. Anything it does not carry is a setting added since it was
# written and comes from the robot's default; anything the robot no longer accepts is
# dropped rather than taking the settings page down with it
def settings_of(row: RobotSettingsRow) -> RobotSettings:
    try:
        return RobotSettings(**row.values)
    except ValidationError as exc:
        bad = {str(error["loc"][0]) for error in exc.errors() if error["loc"]}
        log.warning("stored settings the robot no longer accepts, back to default: %s",
                    ", ".join(sorted(bad)))
        return RobotSettings(**{k: v for k, v in row.values.items() if k not in bad})


# Merge changes over what is stored and count the change. Validation is the settings model's
# own, so a value outside a setting's bounds never reaches the row: it raises here and the
# caller turns it into an answer the operator can read
def update_settings(db, changes: dict) -> tuple[RobotSettingsRow, RobotSettings]:
    row = get_row(db)
    return _store(db, row, RobotSettings(**{**row.values, **changes}))


# Throw away what is stored and start again from the robot's own constants. The version
# carries on counting: the robot has to see a number it has not applied yet
def reset_settings(db) -> tuple[RobotSettingsRow, RobotSettings]:
    return _store(db, get_row(db), RobotSettings())


def _store(db, row, settings):
    row.values  = settings.model_dump()   # a fresh dict, one changed in place goes unnoticed
    row.version = row.version + 1
    db.flush()
    return row, settings
