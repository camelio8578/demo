"""FastAPI dependency injection."""

from __future__ import annotations

from sqlalchemy.orm import Session

from proceeds_navigator.db.session import get_db

__all__ = ["get_db"]
