"""SQLite-backed user accounts and projects for P2-11.

Provides registration, login, project creation, and video/prompt/history
isolation. Designed to work with both SQLite (development) and PostgreSQL
(production) via SQLAlchemy 2.0 core compatibility layer.

Database URL from environment:
- DATABASE_URL or SQLALCHEMY_DATABASE_URL (defaults to ./backend/data/visionprompt.db)
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    create_engine,
    Table,
    MetaData,
)
from sqlalchemy.orm import (
    declarative_base,
    Session,
    relationship,
)

Base = declarative_base()


# ------------------------------------------------------------------
# Association table: projects <-> users (many-to-many)
# ------------------------------------------------------------------
project_users = Table(
    "project_users",
    Base.metadata,
    Column("project_id", Integer, ForeignKey("projects.id"), nullable=False),
    Column("user_id", Integer, ForeignKey("users.id"), nullable=False),
    Column("role", String, default="member"),  # member, owner
)


# ------------------------------------------------------------------
# Database models
# ------------------------------------------------------------------


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    projects = relationship("Project", secondary=project_users, back_populates="owners")
    videos = relationship("Video", back_populates="owner")
    prompt_history = relationship("PromptHistory", back_populates="owner")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    owners = relationship("User", secondary=project_users, back_populates="projects")
    videos = relationship("Video", back_populates="project")
    reference_images = relationship("ReferenceImage", back_populates="project")


class Video(Base):
    __tablename__ = "videos"

    id = Column(Integer, primary_key=True, index=True)
    stored_filename = Column(String, unique=True, index=True, nullable=False)
    original_filename = Column(String, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    status = Column(String, default="uploaded")  # uploaded, processing, completed, failed
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="videos")
    project = relationship("Project", back_populates="videos")
    analyses = relationship("AnalysisResult", back_populates="video")


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    analysis_type = Column(String, nullable=False)  # e.g., "shot_detection", "camera_estimate", etc.
    result_data = Column(Text, nullable=True)  # JSON-serialized
    created_at = Column(DateTime, nullable=False)

    # Relationships
    video = relationship("Video", back_populates="analyses")


class ReferenceImage(Base):
    __tablename__ = "reference_images"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    stored_path = Column(String, nullable=False)
    purpose = Column(String, nullable=False)  # character, appearance, style, composition
    created_at = Column(DateTime, nullable=False)

    # Relationships
    project = relationship("Project", back_populates="reference_images")


class PromptHistory(Base):
    __tablename__ = "prompt_history"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    prompt_text = Column(Text, nullable=False)
    version_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False)

    # Relationships
    owner = relationship("User", back_populates="prompt_history")


# ------------------------------------------------------------------
# Database engine & session helpers
# ------------------------------------------------------------------


def _get_database_url() -> str:
    """Get the database URL from environment or defaults."""
    url = (
        os.environ.get("DATABASE_URL")
        or os.environ.get("SQLALCHEMY_DATABASE_URL")
        or "sqlite:///./data/visionprompt.db"
    )
    return url


def _create_engine_conn() -> Any:
    """Create SQLAlchemy engine."""
    from sqlalchemy import event

    database_url = _get_database_url()

    # SQLite specific settings
    if database_url.startswith("sqlite"):
        engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
        # Enable foreign keys for SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
        return engine

    # PostgreSQL or other RDBMS
    engine = create_engine(database_url, echo=False)
    return engine


_engine: Optional[Any] = None


def get_engine() -> Any:
    """Get or create the database engine (singleton)."""
    global _engine
    if _engine is None:
        _engine = _create_engine_conn()
    return _engine


def init_db() -> None:
    """Initialize database (create all tables)."""
    engine = get_engine()
    Base.metadata.create_all(engine)


def get_session() -> Session:
    """Get a new SQLAlchemy session."""
    from sqlalchemy.orm import sessionmaker

    engine = get_engine()
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return session_factory()


# Convenience: path for SQLite default
def _default_db_path() -> Path:
    """Return the default SQLite database path (project root / data)."""
    # From app/models.py, go up to project root, then into data/
    return Path(__file__).parent.parent / "data" / "visionprompt.db"


# -----------------------------------------------------------------
# Security helpers (password hashing)
# -----------------------------------------------------------------


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt or fallback to simple hash."""
    try:
        import bcrypt

        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except ImportError:
        # Fallback: simple hash for development (NOT secure, for demo only)
        import hashlib
        return hashlib.sha256(password.encode("utf-8")).hexdigest()


def _verify_password(plain_password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    try:
        import bcrypt

        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed.encode("utf-8"))
    except ImportError:
        import hashlib
        return hashlib.sha256(plain_password.encode("utf-8")).hexdigest() == hashed