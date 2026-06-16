"""Entry point — starts shared services and trading bots."""

from __future__ import annotations

import logging
import signal
import sys
import time

from shared.calendar_monitor import CalendarMonitor
from shared.db import ping as db_ping
from shared.model_registry import ModelRegistry
from shared.news_fetcher import NewsFetcher
from shared.oanda_streamer import OandaStreamer
from shared.redis_client import RedisClient
from shared.sentiment_engine import SentimentEngine
from strategies.gold_momentum_v1 import GoldMomentumBot
from strategies.gold_sentiment_v1 import GoldSentimentBot

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_running = True


def _shutdown(signum: int, frame: object) -> None:
    global _running
    logger.info("Shutdown signal received")
    _running = False


def main() -> int:
    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    logger.info("Starting super-trading bot engine")

    redis = RedisClient()
    if not redis.ping():
        logger.error("Cannot connect to Redis — run `make up` first")
        return 1

    if not db_ping():
        logger.error("Cannot connect to PostgreSQL — run `make up` first")
        return 1

    services = [
        NewsFetcher(),
        SentimentEngine(),
        OandaStreamer(),
        CalendarMonitor(),
    ]
    for svc in services:
        svc.start()

    registry = ModelRegistry()
    registry.load("xgb_gold_direction_v2")

    bots = [GoldMomentumBot(), GoldSentimentBot()]
    for bot in bots:
        bot.start()

    logger.info("Bot engine ready — %d bots, %d shared services", len(bots), len(services))

    while _running:
        for bot in bots:
            bot.publish_state()
        time.sleep(5)

    for bot in bots:
        bot.stop()
    for svc in services:
        svc.stop()
    redis.close()

    logger.info("Bot engine stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
