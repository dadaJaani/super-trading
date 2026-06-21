"""Persist candles and trading records to PostgreSQL."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from shared.db import get_connection

logger = logging.getLogger(__name__)


def insert_candle(candle: dict[str, Any]) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO candles (time, instrument, granularity, open, high, low, close, volume)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (time, instrument, granularity) DO NOTHING
            """,
            (
                candle["time"],
                candle["instrument"],
                candle["granularity"],
                candle["open"],
                candle["high"],
                candle["low"],
                candle["close"],
                candle["volume"],
            ),
        )
        conn.commit()


def bulk_insert_candles(candles: list[dict[str, Any]]) -> int:
    if not candles:
        return 0
    with get_connection() as conn:
        for candle in candles:
            conn.execute(
                """
                INSERT INTO candles (time, instrument, granularity, open, high, low, close, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (time, instrument, granularity) DO NOTHING
                """,
                (
                    candle["time"],
                    candle["instrument"],
                    candle["granularity"],
                    candle["open"],
                    candle["high"],
                    candle["low"],
                    candle["close"],
                    candle["volume"],
                ),
            )
        conn.commit()
    return len(candles)


def insert_signal(
    bot_id: str,
    direction: str,
    confidence: float,
    acted_on: bool,
    time: datetime | None = None,
    ml_features: dict[str, Any] | None = None,
) -> None:
    import json

    features_json = json.dumps(ml_features) if ml_features else None
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO signals (bot_id, time, direction, confidence, acted_on, ml_features)
            VALUES (%s, COALESCE(%s, NOW()), %s, %s, %s, %s::jsonb)
            """,
            (bot_id, time, direction, confidence, acted_on, features_json),
        )
        conn.commit()


def insert_trade_open(
    bot_id: str,
    oanda_trade_id: str,
    instrument: str,
    direction: str,
    units: int,
    open_price: float,
    open_time: datetime | None = None,
) -> str:
    with get_connection() as conn:
        row = conn.execute(
            """
            INSERT INTO trades (
                bot_id, oanda_trade_id, instrument, direction, units,
                open_price, open_time, status
            )
            VALUES (%s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()), 'open')
            RETURNING id
            """,
            (bot_id, oanda_trade_id, instrument, direction, units, open_price, open_time),
        ).fetchone()
        conn.commit()
        return str(row[0])


def close_trade_record(
    oanda_trade_id: str,
    close_price: float,
    pnl: float,
    close_time: datetime | None = None,
) -> None:
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE trades
            SET close_price = %s, close_time = COALESCE(%s, NOW()), pnl = %s, status = 'closed'
            WHERE oanda_trade_id = %s AND status = 'open'
            """,
            (close_price, close_time, pnl, oanda_trade_id),
        )
        conn.commit()


def insert_balance_snapshot(
    balance: float,
    nav: float | None = None,
    account_ref: str = "default",
) -> None:
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO balance_snapshots (time, account_ref, balance, nav, source)
            VALUES (%s, %s, %s, %s, 'oanda')
            ON CONFLICT (time, account_ref) DO NOTHING
            """,
            (now, account_ref, balance, nav),
        )
        conn.commit()


def get_bot_config(bot_id: str) -> dict[str, Any]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT config FROM bots WHERE id = %s",
            (bot_id,),
        ).fetchone()
        if not row or row[0] is None:
            return {}
        return dict(row[0])
