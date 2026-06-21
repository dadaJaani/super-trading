"""OANDA price stream → candle aggregation via REST polling."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from shared.candle_backfill import backfill_candles
from shared.oanda_client import OandaClient
from shared.redis_client import RedisClient
from shared.trading_db import insert_candle

logger = logging.getLogger(__name__)

CandleHandler = Callable[[dict[str, Any]], None]


class OandaStreamer:
    """Polls OANDA candles for multiple granularities, stores bars, publishes to Redis."""

    def __init__(
        self,
        redis: RedisClient,
        oanda: OandaClient,
        poll_interval_sec: int = 30,
        instruments: list[str] | None = None,
        granularities: list[str] | None = None,
    ) -> None:
        self._redis = redis
        self._oanda = oanda
        self._poll_interval = poll_interval_sec
        self._instruments = instruments or ["XAU_USD"]
        self._granularities = granularities or ["M5", "H1"]
        self._last_candle_time: dict[str, str] = {}
        self._handlers: list[CandleHandler] = []
        self._thread: threading.Thread | None = None
        self._running = False

    def register_handler(self, handler: CandleHandler) -> None:
        self._handlers.append(handler)

    def start(self, instruments: list[str] | None = None) -> None:
        if instruments:
            self._instruments = instruments

        for instrument in self._instruments:
            for granularity in self._granularities:
                backfill_candles(self._oanda, instrument, granularity, count=120)
                candles = self._oanda.get_candles(instrument, granularity=granularity, count=1)
                if candles:
                    key = f"{instrument}:{granularity}"
                    self._last_candle_time[key] = candles[-1]["time"]

        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info(
            "OandaStreamer started %s %s poll=%ds",
            self._instruments,
            self._granularities,
            self._poll_interval,
        )

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=self._poll_interval + 5)
        logger.info("OandaStreamer stopped")

    def _poll_loop(self) -> None:
        while self._running:
            for instrument in self._instruments:
                for granularity in self._granularities:
                    try:
                        self._poll_candles(instrument, granularity)
                    except Exception:
                        logger.exception("Failed polling %s %s", instrument, granularity)
            time.sleep(self._poll_interval)

    def _poll_candles(self, instrument: str, granularity: str) -> None:
        candles = self._oanda.get_candles(instrument, granularity=granularity, count=2)
        if not candles:
            return

        latest = candles[-1]
        key = f"{instrument}:{granularity}"
        candle_time = latest["time"]
        prev = self._last_candle_time.get(key)
        if prev == candle_time:
            return

        self._last_candle_time[key] = candle_time
        insert_candle(latest)

        channel = f"candles:{instrument}:{granularity}"
        self._redis.publish(channel, latest)
        logger.info(
            "New %s %s candle %s close=%.2f",
            instrument,
            granularity,
            candle_time,
            latest["close"],
        )

        for handler in self._handlers:
            try:
                handler(latest)
            except Exception:
                logger.exception("Candle handler failed for %s %s", instrument, granularity)
