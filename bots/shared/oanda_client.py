"""OANDA v20 REST client wrapper."""

from __future__ import annotations

import logging
from typing import Any

from oandapyV20 import API
import oandapyV20.endpoints.accounts as accounts
import oandapyV20.endpoints.instruments as instruments
import oandapyV20.endpoints.orders as orders
import oandapyV20.endpoints.pricing as pricing
import oandapyV20.endpoints.trades as trades

from shared.config import settings

logger = logging.getLogger(__name__)


class OandaClient:
    """Thin wrapper around oandapyV20 for paper trading."""

    def __init__(
        self,
        api_key: str | None = None,
        account_id: str | None = None,
        env: str | None = None,
        account_ref: str | None = None,
    ) -> None:
        key = (api_key or settings.oanda_api_key).strip()
        acc = (account_id or settings.oanda_account_id).strip()
        environment = (env or settings.oanda_env).lower()

        if not key or not acc:
            raise ValueError(
                "OANDA credentials required — set constructor args or "
                "OANDA_API_KEY / OANDA_ACCOUNT_ID in .env"
            )

        if environment not in ("practice", "live"):
            raise ValueError(f"OANDA env must be 'practice' or 'live', got {environment!r}")

        self._account_id = acc
        self._account_ref = account_ref or "default"
        self._api = API(access_token=key, environment=environment)
        logger.info(
            "OandaClient initialized (%s account %s ref=%s)",
            environment,
            self._account_id,
            self._account_ref,
        )

    @property
    def account_id(self) -> str:
        return self._account_id

    @property
    def account_ref(self) -> str:
        return self._account_ref

    def _request(self, request: Any) -> dict[str, Any]:
        response = self._api.request(request)
        return response if isinstance(response, dict) else {}

    def get_account_summary(self) -> dict[str, Any]:
        response = self._request(accounts.AccountSummary(self._account_id))
        return response.get("account", {})

    def get_candles(
        self,
        instrument: str,
        granularity: str = "H1",
        count: int = 50,
    ) -> list[dict[str, Any]]:
        params = {"count": count, "granularity": granularity, "price": "M"}
        response = self._request(
            instruments.InstrumentsCandles(instrument=instrument, params=params)
        )
        candles = response.get("candles", [])
        result: list[dict[str, Any]] = []
        for candle in candles:
            if not candle.get("complete", False):
                continue
            mid = candle.get("mid", {})
            result.append(
                {
                    "time": candle["time"],
                    "instrument": instrument,
                    "granularity": granularity,
                    "open": float(mid.get("o", 0)),
                    "high": float(mid.get("h", 0)),
                    "low": float(mid.get("l", 0)),
                    "close": float(mid.get("c", 0)),
                    "volume": int(candle.get("volume", 0)),
                    "complete": True,
                }
            )
        return result

    def get_latest_price(self, instrument: str) -> float | None:
        params = {"instruments": instrument}
        response = self._request(pricing.PricingInfo(self._account_id, params=params))
        prices = response.get("prices", [])
        if not prices:
            return None
        bid = prices[0].get("bids", [{}])[0].get("price")
        ask = prices[0].get("asks", [{}])[0].get("price")
        if bid and ask:
            return (float(bid) + float(ask)) / 2
        return None

    def get_open_trades(self) -> list[dict[str, Any]]:
        response = self._request(trades.OpenTrades(self._account_id))
        raw_trades = response.get("trades", [])
        result: list[dict[str, Any]] = []
        for trade in raw_trades:
            units = int(float(trade.get("currentUnits", 0)))
            direction = "LONG" if units > 0 else "SHORT"
            result.append(
                {
                    "oanda_trade_id": trade.get("id"),
                    "instrument": trade.get("instrument"),
                    "direction": direction,
                    "units": abs(units),
                    "open_price": float(trade.get("price", 0)),
                    "current_price": float(trade.get("price", 0)),
                    "unrealized_pl": float(trade.get("unrealizedPL", 0)),
                    "open_time": trade.get("openTime"),
                }
            )
        return result

    def get_open_trade_for_instrument(self, instrument: str) -> dict[str, Any] | None:
        for trade in self.get_open_trades():
            if trade.get("instrument") == instrument:
                current = self.get_latest_price(instrument)
                if current is not None:
                    trade["current_price"] = current
                return trade
        return None

    def create_market_order(self, instrument: str, units: int) -> dict[str, Any]:
        data = {
            "order": {
                "units": str(units),
                "instrument": instrument,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT",
            }
        }
        response = self._request(orders.OrderCreate(self._account_id, data=data))
        logger.info("Market order placed: %s units=%s", instrument, units)
        return response

    def close_trade(self, oanda_trade_id: str) -> dict[str, Any]:
        data = {"units": "ALL"}
        response = self._request(
            trades.TradeClose(self._account_id, oanda_trade_id, data=data)
        )
        logger.info("Closed OANDA trade %s", oanda_trade_id)
        return response
