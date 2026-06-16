"""Redis pub/sub wrapper."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

import redis

from shared.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """Thin wrapper around Redis publish/subscribe."""

    def __init__(self) -> None:
        self._client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        self._pubsub = self._client.pubsub()

    def ping(self) -> bool:
        try:
            self._client.ping()
            logger.info("Redis connection OK")
            return True
        except Exception:
            logger.exception("Redis connection failed")
            return False

    def publish(self, channel: str, message: dict[str, Any]) -> None:
        self._client.publish(channel, json.dumps(message))
        logger.debug("Published to %s: %s", channel, message)

    def subscribe(self, channels: list[str], handler: Callable[[str, dict], None]) -> None:
        self._pubsub.subscribe(**{ch: handler for ch in channels})
        logger.info("Subscribed to channels: %s", channels)

    def close(self) -> None:
        self._pubsub.close()
        self._client.close()
