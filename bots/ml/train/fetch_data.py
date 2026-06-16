"""Download historical candles from OANDA or DB."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def fetch(instrument: str = "XAU_USD", granularity: str = "H1", years: int = 3) -> None:
    logger.info("fetch_data (stub): %s %s %dy", instrument, granularity, years)
