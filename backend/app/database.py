from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

IS_SQLITE = settings.DATABASE_URL.startswith("sqlite")

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if IS_SQLITE else {},
    pool_pre_ping=True,
)


if IS_SQLITE:

    @event.listens_for(engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.execute("PRAGMA busy_timeout=5000")
        cur.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def _migrate_sqlite(conn) -> None:
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())
    columns = {t: {c["name"] for c in inspector.get_columns(t)} for t in tables}

    if "runs" in tables and "name" not in columns["runs"]: 
        conn.execute(text("ALTER TABLE runs ADD COLUMN name VARCHAR(120) NOT NULL DEFAULT ''"))
        # Runs recorded before the column get the label the UI already shows
        conn.execute(text("UPDATE runs SET name = 'Run ' || substr(id, 1, 8) WHERE name = ''"))

    if "defects" in tables: 
        if "pos_to_start" not in columns["defects"] and "distance_to_start_m" in columns["defects"]: 
            conn.execute(text("ALTER TABLE defects RENAME COLUMN distance_to_start_m TO pos_to_start"))

        if "created_at" not in columns["defects"]: 
            conn.execute(text(
                "ALTER TABLE defects ADD COLUMN created_at DATETIME NOT NULL "
                "DEFAULT '1970-01-01 00:00:00'"
            ))
            # Best available timestamp for older defects: when their run started
            conn.execute(text(
                "UPDATE defects SET created_at = "
                "(SELECT started_at FROM runs WHERE runs.id = defects.run_id) "
                "WHERE created_at = '1970-01-01 00:00:00' AND run_id IN (SELECT id FROM runs)"
            ))

        # What the vision model reports, nullable so older rows stay valid
        for column, ddl in (
            ("label", "label VARCHAR(64)"),
            ("confidence", "confidence FLOAT"),
            ("cam", "cam INTEGER"),
            ("box_x1", "box_x1 FLOAT"),
            ("box_y1", "box_y1 FLOAT"),
            ("box_x2", "box_x2 FLOAT"),
            ("box_y2", "box_y2 FLOAT"),
        ):
            if column not in columns["defects"]:
                conn.execute(text(f"ALTER TABLE defects ADD COLUMN {ddl}"))

        # Databases created while defects were placed relative to anchors (1da035e) were
        # never moved off them: f9bba4c dropped anchors without a migration, so they still
        # carry anchor_id and distance_to_anchor_m, both NOT NULL, and have no pos_to_start.
        # Every read fails on the missing column and every insert on the NOT NULL ones.
        # SQLite cannot drop a column that is indexed and a foreign key, so the table is
        # rebuilt. The anchor's distance from the origin plus the defect's distance from the
        # anchor is the position the app works with.
        if "pos_to_start" not in columns["defects"] and "distance_to_anchor_m" in columns["defects"]:
            anchor = (
                "COALESCE((SELECT distance_to_origin_m FROM anchors "
                "WHERE anchors.id = old.anchor_id), 0) + "
                if "anchors" in tables else ""
            )
            conn.execute(text("ALTER TABLE defects RENAME TO defects_anchored"))

            # the renamed table keeps its index names, the rebuilt one needs them back
            for (name,) in conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type = 'index' "
                "AND tbl_name = 'defects_anchored' AND sql IS NOT NULL"
            )).all():
                conn.execute(text(f'DROP INDEX "{name}"'))

            Base.metadata.tables["defects"].create(conn)
            conn.execute(text(
                "INSERT INTO defects (id, run_id, kind, pos_to_start, created_at, "
                "label, confidence, cam, box_x1, box_y1, box_x2, box_y2) "
                f"SELECT id, run_id, kind, {anchor}distance_to_anchor_m, created_at, "
                "label, confidence, cam, box_x1, box_y1, box_x2, box_y2 "
                "FROM defects_anchored AS old"
            ))
            conn.execute(text("DROP TABLE defects_anchored"))


def init_db() -> None:
    import app.models  

    Base.metadata.create_all(bind=engine)


    if IS_SQLITE:
        with engine.begin() as conn:
            _migrate_sqlite(conn)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# transaction session
@contextmanager
def session_scope() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()