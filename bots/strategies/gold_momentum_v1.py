"""Gold momentum bot — XAU/USD technical + ML strategy."""

from __future__ import annotations

from typing import Any

from strategies.base_bot import BaseBot


class GoldMomentumBot(BaseBot):
    id = "gold_momentum_v1"
    instrument = "XAU_USD"
    strategy = "momentum"
    uses_models = ["xgb_gold_direction_v2"]
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
