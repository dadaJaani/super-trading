"""Pushover push notifications."""

from __future__ import annotations

import logging

from shared.config import settings

logger = logging.getLogger(__name__)


def notify(title: str, message: str, priority: int = 0) -> None:
    """Send a push notification via Pushover."""
    if not settings.pushover_token or not settings.pushover_user:
        logger.debug("Pushover not configured — skipping: %s: %s", title, message)
        return
    logger.info("Notify (stub) [%s] %s: %s", priority, title, message)
