"""Gold sentiment bot — XAU/USD news-driven strategy."""

from __future__ import annotations

from typing import Any

from strategies.base_bot import BaseBot


class GoldSentimentBot(BaseBot):
    id = "gold_sentiment_v1"
    instrument = "XAU_USD"
    strategy = "sentiment"
    uses_models = []
    uses_sentiment = True

    def on_candle(self, candle: dict[str, Any]) -> None:
        pass

    def on_sentiment(self, score: float) -> None:
        pass

    def on_calendar_alert(self, event: dict[str, Any]) -> None:
        pass

    def evaluate_signal(self) -> dict[str, Any] | None:
        return None

    def execute(self, direction: str, size: int) -> None:
        pass
