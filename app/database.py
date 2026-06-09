"""
app/database.py — Database connection & session management

Responsibilities:
- Create the SQLAlchemy engine connected to SQLite
- Provide a session factory (SessionLocal) for DB operations
- Expose `get_db()` — a context manager used throughout the app
- Call `init_db()` on startup to create all tables if they don't exist
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from contextlib import contextmanager

from config import DATABASE_URL, DEBUG


# ── Base class all ORM models inherit from ────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Engine: one per process, handles connection pooling ───────────────────────
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Required for SQLite
    echo=DEBUG,   # Logs SQL when DEBUG=true — useful for development
)

# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


@contextmanager
def get_db():
    """
    Context manager that yields a DB session and handles
    commit/rollback/close automatically.

    Usage:
        with get_db() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """
    Creates all database tables defined in models.py.
    Safe to call multiple times — only creates tables that don't exist yet.
    """
    # Import models here so Base.metadata is populated before create_all
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
