"""Economic calendar event watcher."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class CalendarMonitor:
    """Monitors high-impact economic events and broadcasts alerts."""

    REDIS_CHANNEL = "calendar:alert"
    ALERT_MINUTES_BEFORE = 30

    def start(self) -> None:
        logger.info("CalendarMonitor started (stub)")

    def stop(self) -> None:
        logger.info("CalendarMonitor stopped")

    def check_upcoming_events(self) -> list[dict]:
        """Return upcoming high-impact events."""
        logger.debug("Checking calendar (stub)")
        return []
