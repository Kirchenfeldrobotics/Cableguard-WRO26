# Deletes the detections that were stored before the robot dropped the boxes beside the rope
# itself, see RobotSettings.on_rope in comm_protocols/settings.py.
#
#   cd backend
#   python -m scripts.drop_beside_rope            # list what lies beside the rope, delete nothing
#   python -m scripts.drop_beside_rope --apply    # delete it, there is no way back
#
# The rope is where the operator's settings say it is, so set the two ignored strips on the
# settings page first. A detection is judged by its box, as on the robot; a defect from another
# sensor has no box and is left alone. The frame a deleted detection was found in goes with it,
# unless a detection that stays was found in the same frame.

import argparse
from collections import defaultdict

from sqlalchemy import func, inspect, select

from app.database import engine, session_scope
from app.models import Defect, Frame, RobotSettingsRow, Rope, Run
from app.repository import defects as defects_repo
from app.repository import settings as settings_repo
from comm_protocols.settings import RobotSettings


def main():
    parser = argparse.ArgumentParser(
        description="Delete stored detections whose box lies beside the rope.")
    parser.add_argument("--apply", action="store_true",
                        help="delete the detections, not only list them")
    args = parser.parse_args()

    # init_db() is not called: on a database built for another schema it drops every table,
    # and this is run on one that holds runs worth keeping
    if not inspect(engine).has_table("defects"):
        print(f"no runs stored at {engine.url}")
        return

    with session_scope() as db:
        # read and not get_row, which writes the defaults when nothing is stored
        row = db.get(RobotSettingsRow, 1)
        settings = settings_repo.settings_of(row) if row is not None else RobotSettings()
        source = f"settings version {row.version}" if row is not None else "no settings stored, the robot's defaults"
        print(f"on the rope: box centre between {settings.detect_ignore_top:g} % and "
              f"{100.0 - settings.detect_ignore_bottom:g} % of the frame height ({source})")

        boxed = db.execute(
            select(Defect, Run, Rope)
            .join(Run, Defect.run_id == Run.id)
            .join(Rope, Run.rope_id == Rope.id)
            .where(Defect.box_y1.is_not(None), Defect.box_y2.is_not(None))
            .order_by(Rope.name, Run.started_at, Defect.pos_to_start)
        ).all()

        checked = defaultdict(int)
        beside = defaultdict(list)
        for defect, run, rope in boxed:
            checked[run.id] += 1
            if not settings.on_rope(defect.box_y1, defect.box_y2):
                beside[(rope.name, run.name, run.id)].append(defect)

        for (rope_name, run_name, run_id), defects in beside.items():
            print(f"\n{rope_name} / {run_name}: {len(defects)} of {checked[run_id]} detection(s) beside the rope")
            for d in defects:
                centre = (d.box_y1 + d.box_y2) / 2.0 * 100.0
                print(f"  {d.pos_to_start:8.2f} m  {d.label or d.kind:<18} {d.confidence or 0.0:.2f}  "
                      f"cam{d.cam}  centre at {centre:.0f} %")

        found = [d for defects in beside.values() for d in defects]
        if not found:
            print(f"\nevery stored detection lies on the rope ({len(boxed)} checked), nothing to delete")
            return
        if not args.apply:
            print(f"\n{len(found)} of {len(boxed)} detection(s) beside the rope, nothing deleted. "
                  "Pass --apply to delete them")
            return

        frames = db.scalar(select(func.count()).select_from(Frame))
        defects_repo.delete_defects(db, [d.id for d in found])
        db.flush()
        frames -= db.scalar(select(func.count()).select_from(Frame))

    print(f"\n{len(found)} detection(s) deleted, and {frames} frame(s) no detection was left in")


if __name__ == "__main__":
    main()
