"""Track OANDA account balance and publish snapshots."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from shared.oanda_client import OandaClient
from shared.trading_db import insert_balance_snapshot

if TYPE_CHECKING:
    from shared.redis_client import RedisClient

logger = logging.getLogger(__name__)


class BalanceTracker:
    """Periodically snapshots OANDA NAV to DB and Redis."""

    def __init__(
        self,
        redis: RedisClient,
        oanda: OandaClient,
        interval_sec: int = 300,
        account_ref: str | None = None,
    ) -> None:
        self._redis = redis
        self._oanda = oanda
        self._interval = interval_sec
        self._account_ref = account_ref or oanda.account_ref
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self) -> None:
        self._running = True
        self.snapshot()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        logger.info("BalanceTracker started (interval %ds)", self._interval)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=self._interval + 5)
        logger.info("BalanceTracker stopped")

    def snapshot(self) -> None:
        try:
            account = self._oanda.get_account_summary()
            balance = float(account.get("balance", 0))
            nav = float(account.get("NAV", balance))
            now = datetime.now(timezone.utc).isoformat()
            insert_balance_snapshot(balance, nav, account_ref=self._account_ref)
            self._redis.publish(
                "balance:update",
                {
                    "time": now,
                    "balance": balance,
                    "nav": nav,
                    "accountRef": self._account_ref,
                },
            )
            logger.info("Balance snapshot: balance=%.2f nav=%.2f", balance, nav)
        except Exception:
            logger.exception("Failed to snapshot balance")

    def _loop(self) -> None:
        while self._running:
            time.sleep(self._interval)
            if self._running:
                self.snapshot()
