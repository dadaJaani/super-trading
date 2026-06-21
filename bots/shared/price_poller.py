"""Poll OANDA mid prices and publish to Redis."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from shared.oanda_client import OandaClient

if TYPE_CHECKING:
    from shared.redis_client import RedisClient

logger = logging.getLogger(__name__)


class PricePoller:
    """Periodically fetches latest mid price for instruments."""

    def __init__(
        self,
        redis: RedisClient,
        oanda: OandaClient,
        instruments: list[str] | None = None,
        interval_sec: int = 15,
    ) -> None:
        self._redis = redis
        self._oanda = oanda
        self._instruments = instruments or ["XAU_USD"]
        self._interval = interval_sec
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self._poll_once()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("PricePoller started (%ds) %s", self._interval, self._instruments)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=self._interval + 5)
        logger.info("PricePoller stopped")

    def _poll_once(self) -> None:
        now = datetime.now(timezone.utc).isoformat()
        for instrument in self._instruments:
            try:
                price = self._oanda.get_latest_price(instrument)
                if price is None:
                    continue
                self._redis.publish(
                    f"price:{instrument}",
                    {"time": now, "instrument": instrument, "price": price},
                )
            except Exception:
                logger.exception("Price poll failed for %s", instrument)

    def _loop(self) -> None:
        while self._running:
            time.sleep(self._interval)
            if self._running:
                self._poll_once()
