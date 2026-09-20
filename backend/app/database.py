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