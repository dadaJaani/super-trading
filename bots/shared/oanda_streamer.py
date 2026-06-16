"""OANDA price stream → candle aggregation."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class OandaStreamer:
    """Streams ticks from OANDA, aggregates candles, stores to TimescaleDB."""

    def start(self, instruments: list[str] | None = None) -> None:
        instruments = instruments or ["XAU_USD"]
        logger.info("OandaStreamer started for %s (stub)", instruments)

    def stop(self) -> None:
        logger.info("OandaStreamer stopped")

    def on_tick(self, tick: dict[str, Any]) -> None:
        """Handle incoming tick data."""
        logger.debug("Tick received (stub): %s", tick)
