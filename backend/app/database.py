import logging
from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

log = logging.getLogger(__name__)

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


# Bump this whenever a model changes. The database records the version it was built for,
# and one built for any other is dropped and rebuilt from the models. The data is expendable,
# a schema that only half matches the code is not: every missing column is a 500 on a page.
SCHEMA_VERSION = 1


def _rebuild_if_stale() -> None:
    # raw connection: foreign keys can only be switched off outside a transaction, and with
    # them off the tables can be dropped in any order, including ones no model knows anymore
    raw = engine.raw_connection()
    try:
        cur = raw.cursor()
        found = cur.execute("PRAGMA user_version").fetchone()[0]
        if found == SCHEMA_VERSION:
            return

        tables = [row[0] for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )]
        cur.execute("PRAGMA foreign_keys=OFF")
        for table in tables:
            cur.execute(f'DROP TABLE "{table}"')
        cur.execute("PRAGMA foreign_keys=ON")
        raw.commit()
        if tables:
            log.warning("database schema %d does not match %d, dropped %d tables and rebuilt",
                        found, SCHEMA_VERSION, len(tables))
    finally:
        raw.close()


def init_db() -> None:
    import app.models  

    if IS_SQLITE:
        _rebuild_if_stale()

    Base.metadata.create_all(bind=engine)

    if IS_SQLITE:
        with engine.begin() as conn:
            conn.exec_driver_sql(f"PRAGMA user_version = {SCHEMA_VERSION}")


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