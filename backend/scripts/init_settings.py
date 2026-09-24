# Writes the robot's own constants into the database as the operator's settings, once.
#
#   cd backend
#   python -m scripts.init_settings            # only if there are none stored yet
#   python -m scripts.init_settings --force    # throw away what is stored and start again
#
# The backend creates the row by itself the first time the settings page is opened, so this
# is for setting the database up before anyone looks at it, and for putting a robot that was
# configured into a corner back on its defaults.

import argparse

from app.database import init_db, session_scope
from app.models import RobotSettingsRow
from app.repository import settings as settings_repo
from comm_protocols.settings import GROUPS, describe_settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true",
                        help="overwrite settings that are already stored")
    args = parser.parse_args()

    init_db()

    with session_scope() as db:
        stored = db.get(RobotSettingsRow, 1)

        if stored is not None and not args.force:
            print(f"settings already stored, version {stored.version}, "
                  f"last changed {stored.updated_at:%Y-%m-%d %H:%M}")
            print("nothing written. Pass --force to put them back on the robot's defaults")
            return

        # get_row writes the defaults when there is no row yet, reset puts an existing
        # one back on them and counts the change so the robot sees a new version
        row = settings_repo.reset_settings(db)[0] if stored is not None else settings_repo.get_row(db)
        version = row.version

    # the robot picks the new version up on its next connect, or from the settings page
    by_group = {}
    for field in describe_settings():
        by_group.setdefault(field.group, []).append(field)

    for key, title, _ in GROUPS:
        print(f"\n{title}")
        for field in by_group.get(key, []):
            value = f"{field.default:g}"
            print(f"  {field.label:<24} {value:>10} {field.unit}")

    print(f"\n{len(describe_settings())} settings written as version {version}. "
          "A connected robot is told on its next connect, or from the settings page.")


if __name__ == "__main__":
    main()
