"""PostgreSQL connection helper."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Generator

import psycopg

from shared.config import settings

logger = logging.getLogger(__name__)


def get_connection_string() -> str:
    return settings.database_url


@contextmanager
def get_connection() -> Generator[psycopg.Connection, None, None]:
    """Yield a PostgreSQL connection."""
    conn = psycopg.connect(get_connection_string())
    try:
        yield conn
    finally:
        conn.close()


def ping() -> bool:
    """Verify database connectivity."""
    try:
        with get_connection() as conn:
            conn.execute("SELECT 1")
        logger.info("Database connection OK")
        return True
    except Exception:
        logger.exception("Database connection failed")
        return False
