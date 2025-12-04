"""
GEO Data Points Database Connection

Provides database engine, session management, and initialization.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import os
from typing import Generator

from .models import Base


# Database configuration
DATABASE_URL = os.getenv(
    "GEO_DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/geo_platform"
)

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    echo=False  # Set to True for SQL query logging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_database():
    """
    Initialize database tables.

    Creates all tables defined in models.py if they don't exist.
    Safe to call multiple times (won't recreate existing tables).
    """
    Base.metadata.create_all(bind=engine)
    print(f"✓ GEO Data Points database tables initialized")


def drop_all_tables():
    """
    Drop all GEO data points tables.

    WARNING: This will delete all data! Use only for development/testing.
    """
    Base.metadata.drop_all(bind=engine)
    print(f"✗ GEO Data Points database tables dropped")


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Usage:
        with get_db_session() as db:
            result = db.query(Analysis).first()

    Automatically commits on success, rolls back on exception.
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection for FastAPI routes.

    Usage in FastAPI:
        @app.get("/results")
        def get_results(db: Session = Depends(get_db)):
            return db.query(Analysis).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
