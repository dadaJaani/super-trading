"""Backfill historical candles from OANDA into Postgres."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from shared.trading_db import bulk_insert_candles

if TYPE_CHECKING:
    from shared.oanda_client import OandaClient

logger = logging.getLogger(__name__)

DEFAULT_COUNT = 120


def backfill_candles(
    oanda: OandaClient,
    instrument: str,
    granularity: str,
    count: int = DEFAULT_COUNT,
) -> int:
    """Fetch completed candles from OANDA and insert into DB."""
    candles = oanda.get_candles(instrument, granularity=granularity, count=count)
    if not candles:
        logger.warning("No candles to backfill for %s %s", instrument, granularity)
        return 0

    inserted = bulk_insert_candles(candles)
    logger.info("Backfilled %d/%d %s %s candles", inserted, len(candles), instrument, granularity)
    return inserted
