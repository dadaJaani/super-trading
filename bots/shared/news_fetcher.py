"""RSS + Finnhub news poller."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class NewsFetcher:
    """Polls news sources and publishes raw headlines to Redis."""

    REDIS_CHANNEL = "news:raw"
    POLL_INTERVAL_SECONDS = 120

    def start(self) -> None:
        logger.info("NewsFetcher started (stub)")

    def stop(self) -> None:
        logger.info("NewsFetcher stopped")

    def poll_once(self) -> None:
        """Fetch headlines and store in PostgreSQL + publish to Redis."""
        logger.debug("NewsFetcher poll (stub)")
