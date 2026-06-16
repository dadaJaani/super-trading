"""Abstract base class for all trading bots."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseBot(ABC):
    id: str = "base_bot"
    instrument: str = "XAU_USD"
    strategy: str = "base"
    uses_models: list[str] = []
    uses_sentiment: bool = False

    def __init__(self) -> None:
        self._running = False

    def start(self) -> None:
        self._running = True
        logger.info("Bot %s started", self.id)

    def stop(self) -> None:
        self._running = False
        logger.info("Bot %s stopped", self.id)

    @abstractmethod
    def on_candle(self, candle: dict[str, Any]) -> None:
        """Called on each candle close."""

    @abstractmethod
    def on_sentiment(self, score: float) -> None:
        """Called when a new LLM sentiment score arrives."""

    @abstractmethod
    def on_calendar_alert(self, event: dict[str, Any]) -> None:
        """Called before high-impact economic events."""

    @abstractmethod
    def evaluate_signal(self) -> dict[str, Any] | None:
        """Combine inputs and return a signal decision."""

    @abstractmethod
    def execute(self, direction: str, size: int) -> None:
        """Send order to OANDA."""

    def publish_state(self) -> None:
        """Push current state to Redis for the dashboard."""
        logger.debug("Publishing state for %s (stub)", self.id)
