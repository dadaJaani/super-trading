"""Shared SMA crossover bot logic."""

from __future__ import annotations

import logging
from typing import Any

from strategies.base_bot import BaseBot

logger = logging.getLogger(__name__)


def sma(values: list[float], period: int) -> float | None:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def extract_trade_id(response: dict[str, Any]) -> str | None:
    fill = response.get("orderFillTransaction") or {}
    trade_opened = fill.get("tradeOpened")
    if trade_opened:
        return str(trade_opened.get("tradeID"))
    return None


def extract_close_pl(response: dict[str, Any]) -> float:
    fill = response.get("orderFillTransaction") or {}
    return float(fill.get("pl", 0))


class SmaCrossBot(BaseBot):
    """SMA fast/slow crossover with flip-on-cross paper execution."""

    strategy = "sma_cross"
    uses_models: list[str] = []
    uses_sentiment = False

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._closes: list[float] = []
        self._fast_period = 9
        self._slow_period = 21
        self._units = 1
        self._granularity = "H1"
        self._execute_trades = True
        self._last_signal: dict[str, Any] | None = None
        self._open_trade: dict[str, Any] | None = None
        self._bot_params: dict[str, Any] | None = None

    def start(self) -> None:
        super().start()
        if self._oanda is None:
            logger.error("%s requires OandaClient", self.id)
            return

        from shared.decision_logger import log_decision

        config = self._bot_params if self._bot_params is not None else {}
        if not config:
            from shared.trading_db import get_bot_config

            config = get_bot_config(self.id)
        self._fast_period = int(config.get("fast_period", 9))
        self._slow_period = int(config.get("slow_period", 21))
        self._units = int(config.get("units", 1))
        self._granularity = str(config.get("granularity", "H1"))
        self._execute_trades = bool(config.get("execute_trades", True))

        candles = self._oanda.get_candles(
            self.instrument,
            granularity=self._granularity,
            count=max(50, self._slow_period + 5),
        )
        self._closes = [c["close"] for c in candles]
        logger.info(
            "%s warmed %d closes fast=%d slow=%d units=%d %s execute=%s",
            self.id,
            len(self._closes),
            self._fast_period,
            self._slow_period,
            self._units,
            self._granularity,
            self._execute_trades,
        )
        log_decision(
            self.id,
            "bot_started",
            extra=f"granularity={self._granularity} execute_trades={self._execute_trades}",
        )

        open_trade = self._oanda.get_open_trade_for_instrument(self.instrument)
        if open_trade:
            self._open_trade = open_trade

    def on_candle(self, candle: dict[str, Any]) -> None:
        if candle.get("instrument") != self.instrument:
            return
        if candle.get("granularity") != self._granularity:
            return

        from shared.decision_logger import log_decision, log_evaluation

        close = float(candle["close"])
        if self._closes and self._closes[-1] == close:
            return

        self._closes.append(close)
        if len(self._closes) > 500:
            self._closes = self._closes[-500:]

        if len(self._closes) < self._slow_period + 1:
            log_decision(
                self.id,
                "warming",
                candle_close=close,
                extra=f"closes={len(self._closes)} need={self._slow_period + 1}",
            )
            return

        prev_closes = self._closes[:-1]
        fast_prev = sma(prev_closes, self._fast_period)
        slow_prev = sma(prev_closes, self._slow_period)
        fast_now = sma(self._closes, self._fast_period)
        slow_now = sma(self._closes, self._slow_period)

        if fast_prev is None or slow_prev is None or fast_now is None or slow_now is None:
            return

        cross_up = fast_prev <= slow_prev and fast_now > slow_now
        cross_down = fast_prev >= slow_prev and fast_now < slow_now
        cross = "up" if cross_up else "down" if cross_down else None

        log_evaluation(self.id, candle, fast_now, slow_now, cross)

        if cross_up:
            self._handle_signal("LONG", candle, fast_now, slow_now, "cross_up")
        elif cross_down:
            self._handle_signal("SHORT", candle, fast_now, slow_now, "cross_down")
        else:
            self._record_signal("HOLD", candle, fast_now, slow_now, cross, acted=False)

    def _ml_features(
        self,
        candle: dict[str, Any],
        fast_now: float,
        slow_now: float,
        cross_label: str | None,
    ) -> dict[str, Any]:
        cross = None
        if cross_label:
            cross = cross_label.replace("cross_", "")
        return {
            "close": float(candle["close"]),
            "sma_fast": fast_now,
            "sma_slow": slow_now,
            "cross": cross,
            "granularity": self._granularity,
        }

    def _record_signal(
        self,
        direction: str,
        candle: dict[str, Any],
        fast_now: float,
        slow_now: float,
        cross_label: str | None,
        acted: bool,
        confidence: float = 0.5,
    ) -> None:
        from shared.trading_db import insert_signal

        ml_features = self._ml_features(candle, fast_now, slow_now, cross_label)
        self._last_signal = {
            "direction": direction,
            "confidence": confidence,
            "time": candle.get("time"),
            "trigger": "sma_cross" if direction != "HOLD" else "sma_eval",
        }

        insert_signal(
            self.id,
            direction,
            confidence,
            acted,
            ml_features=ml_features,
        )

    def _handle_signal(
        self,
        direction: str,
        candle: dict[str, Any],
        fast_now: float,
        slow_now: float,
        cross_label: str,
    ) -> None:
        from shared.decision_logger import log_decision

        confidence = 0.8
        ml_features = self._ml_features(candle, fast_now, slow_now, cross_label)
        self._last_signal = {
            "direction": direction,
            "confidence": confidence,
            "time": candle.get("time"),
            "trigger": "sma_cross",
        }

        if self._redis:
            self._redis.publish(
                f"signal:{self.id}",
                {"bot_id": self.id, **self._last_signal, "ml_features": ml_features},
            )

        acted = False
        if self._execute_trades:
            acted = self._execute_flip(direction, float(candle["close"]))
        else:
            log_decision(
                self.id,
                "shadow_signal",
                candle_close=float(candle["close"]),
                sma_fast=fast_now,
                sma_slow=slow_now,
                signal=direction,
                extra=cross_label,
            )

        self._record_signal(direction, candle, fast_now, slow_now, cross_label, acted, confidence)
        log_decision(
            self.id,
            cross_label,
            candle_close=float(candle["close"]),
            sma_fast=fast_now,
            sma_slow=slow_now,
            signal=direction,
            acted=acted,
        )

    def _execute_flip(self, direction: str, price: float) -> bool:
        if self._oanda is None:
            return False

        from shared.decision_logger import log_decision
        from shared.trading_db import close_trade_record, insert_trade_open

        current = self._oanda.get_open_trade_for_instrument(self.instrument)
        target_units = self._units if direction == "LONG" else -self._units

        if current:
            if current["direction"] == direction:
                return False

            from shared.trade_console import log_trade_console

            close_resp = self._oanda.close_trade(current["oanda_trade_id"])
            pnl = extract_close_pl(close_resp)
            close_trade_record(current["oanda_trade_id"], price, pnl)
            log_trade_console(
                "CLOSE",
                self.id,
                self.instrument,
                current["direction"],
                current["units"],
                price,
                pnl=pnl,
                trade_id=current["oanda_trade_id"],
            )
            log_decision(
                self.id,
                "trade_closed",
                extra=f"trade_id={current['oanda_trade_id']} pnl={pnl:.2f}",
            )
            if self._redis:
                self._redis.publish(
                    f"trade:closed:{self.id}",
                    {
                        "bot_id": self.id,
                        "oanda_trade_id": current["oanda_trade_id"],
                        "pnl": pnl,
                        "close_price": price,
                    },
                )
            self._open_trade = None

        response = self._oanda.create_market_order(self.instrument, target_units)
        trade_id = extract_trade_id(response)
        if not trade_id:
            logger.error("No trade ID in order response: %s", response)
            log_decision(self.id, "trade_open_failed", extra=str(response))
            return False

        signed_units = abs(self._units)
        insert_trade_open(
            self.id,
            trade_id,
            self.instrument,
            direction,
            signed_units,
            price,
        )
        self._open_trade = {
            "oanda_trade_id": trade_id,
            "instrument": self.instrument,
            "direction": direction,
            "units": signed_units,
            "open_price": price,
            "current_price": price,
            "unrealized_pl": 0.0,
        }
        log_decision(self.id, "trade_opened", signal=direction, acted=True, trade_id=trade_id)

        from shared.trade_console import log_trade_console

        log_trade_console(
            "OPEN",
            self.id,
            self.instrument,
            direction,
            signed_units,
            price,
            trade_id=trade_id,
        )

        if self._redis:
            self._redis.publish(
                f"trade:opened:{self.id}",
                {
                    "bot_id": self.id,
                    "oanda_trade_id": trade_id,
                    "direction": direction,
                    "units": signed_units,
                    "open_price": price,
                },
            )

        return True

    def on_sentiment(self, score: float) -> None:
        pass

    def on_calendar_alert(self, event: dict[str, Any]) -> None:
        pass

    def evaluate_signal(self) -> dict[str, Any] | None:
        return self._last_signal

    def execute(self, direction: str, size: int) -> None:
        self._execute_flip(direction, 0.0)

    def publish_state(self) -> None:
        if self._redis is None or self._oanda is None:
            return

        open_trade = self._oanda.get_open_trade_for_instrument(self.instrument)
        pnl = 0.0
        open_trade_payload: dict[str, Any] | None = None

        if open_trade:
            self._open_trade = open_trade
            pnl = float(open_trade.get("unrealized_pl", 0))
            open_trade_payload = {
                "direction": open_trade["direction"],
                "units": open_trade["units"],
                "openPrice": open_trade["open_price"],
                "currentPrice": open_trade["current_price"],
                "pnl": pnl,
            }

        self._redis.publish(
            f"bot:state:{self.id}",
            {
                "botId": self.id,
                "pnl": pnl,
                "openTrade": open_trade_payload,
                "lastSignal": self._last_signal,
                "executeTrades": self._execute_trades,
            },
        )
