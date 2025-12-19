import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _default_sqlite_url() -> str:
    db_path = Path(__file__).resolve().parents[2] / "data" / "app.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


DATABASE_URL = os.getenv("JIRA_LITE_DATABASE_URL") or _default_sqlite_url()

# `check_same_thread=False` allows usage across threads (FastAPI default).
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db(run_seed: bool = True) -> None:
    """Create database tables and optionally run seed routines."""
    from .models import Base  # imported here to avoid circulars

    Base.metadata.create_all(bind=engine)

    if not run_seed:
        return

    from .seed import seed_phases  # imported here to avoid circulars
    from .sample_seed import seed_sample_data

    with SessionLocal() as session:
        seed_phases(session)
        seed_sample_data(session)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
