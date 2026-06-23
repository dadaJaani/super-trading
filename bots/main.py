"""Entry point — load bots from JSON config and start services."""

from __future__ import annotations

import logging
import signal
import sys
import time

from shared.balance_tracker import BalanceTracker
from shared.bot_registry import BotRegistry, BrokerClientFactory
from shared.bot_sync import sync_bots_to_db
from shared.db import ping as db_ping
from shared.oanda_streamer import OandaStreamer
from shared.price_poller import PricePoller
from shared.redis_client import RedisClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("trade.console").setLevel(logging.INFO)
logger = logging.getLogger(__name__)

_running = True


def _shutdown(signum: int, frame: object) -> None:
    global _running
    logger.info("Shutdown signal received")
    _running = False


def _build_streamers(
    registry: BotRegistry,
    clients: dict[str, object],
    redis: RedisClient,
) -> list[OandaStreamer]:
    streamers: list[OandaStreamer] = []
    for account_ref, spec in registry.account_stream_specs().items():
        client = clients.get(account_ref)
        if client is None:
            continue
        instruments = sorted(spec["instruments"])
        granularities = sorted(spec["granularities"])
        streamer = OandaStreamer(
            redis,
            client,
            poll_interval_sec=30,
            instruments=instruments,
            granularities=granularities,
        )
        streamers.append(streamer)
    return streamers


def _build_price_pollers(
    registry: BotRegistry,
    clients: dict[str, object],
    redis: RedisClient,
) -> list[PricePoller]:
    pollers: list[PricePoller] = []
    for account_ref, instruments in registry.account_instruments().items():
        client = clients.get(account_ref)
        if client is None:
            continue
        pollers.append(
            PricePoller(redis, client, instruments=sorted(instruments), interval_sec=15)
        )
    return pollers


def _build_balance_trackers(
    registry: BotRegistry,
    clients: dict[str, object],
    redis: RedisClient,
) -> list[BalanceTracker]:
    trackers: list[BalanceTracker] = []
    for account_ref, client in clients.items():
        trackers.append(
            BalanceTracker(redis, client, interval_sec=300, account_ref=account_ref)
        )
    return trackers


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

    try:
        registry = BotRegistry.load()
    except (ValueError, NotImplementedError, FileNotFoundError) as exc:
        logger.error("Bot config error: %s", exc)
        return 1

    sync_bots_to_db(registry)

    factory = BrokerClientFactory(registry)
    try:
        clients = factory.build_clients_for_enabled_bots()
    except (ValueError, NotImplementedError) as exc:
        logger.error("Broker client error: %s", exc)
        return 1

    if not clients:
        logger.error("No enabled bots with registered strategies")
        return 1

    bots = registry.instantiate_bots(redis, clients)
    if not bots:
        logger.error("No bots instantiated — check config and credentials")
        return 1

    streamers = _build_streamers(registry, clients, redis)
    price_pollers = _build_price_pollers(registry, clients, redis)
    balance_trackers = _build_balance_trackers(registry, clients, redis)

    for bot in bots:
        for streamer in streamers:
            streamer.register_handler(bot.on_candle)

    services: list[object] = []
    services.extend(streamers)
    services.extend(price_pollers)
    services.extend(balance_trackers)

    for svc in services:
        svc.start()

    for bot in bots:
        bot.start()

    logger.info(
        "Engine ready — %d bots, %d accounts, %d streamers",
        len(bots),
        len(clients),
        len(streamers),
    )

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
