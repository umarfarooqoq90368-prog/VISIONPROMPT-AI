"""Database initialization and session management for P2-11.

Wraps app.models engine/session helpers for use by API routes.
Designed to work with SQLite (development, default) or PostgreSQL
(production) via environment variable DATABASE_URL.
"""
from __future__ import annotations

import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base, _engine, get_session as _get_session, init_db as _init_db


def init_db() -> None:
    """Initialize database (create all tables if not exist)."""
    _init_db()


def get_session() -> Session:
    """Get a new SQLAlchemy session, initializing DB if needed."""
    init_db()
    return _get_session()