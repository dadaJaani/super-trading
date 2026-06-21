"""Append-only decision log files per bot."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


def _log_path(bot_id: str) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / f"{bot_id}.log"


def log_decision(
    bot_id: str,
    message: str,
    *,
    candle_close: float | None = None,
    sma_fast: float | None = None,
    sma_slow: float | None = None,
    signal: str | None = None,
    acted: bool | None = None,
    trade_id: str | None = None,
    extra: str | None = None,
) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    parts = [ts, message]
    if candle_close is not None:
        parts.append(f"candle_close={candle_close:.2f}")
    if sma_fast is not None and sma_slow is not None:
        parts.append(f"sma_fast={sma_fast:.2f} sma_slow={sma_slow:.2f}")
    if signal:
        parts.append(f"signal={signal}")
    if acted is not None:
        parts.append(f"acted={acted}")
    if trade_id:
        parts.append(f"trade_id={trade_id}")
    if extra:
        parts.append(extra)

    line = " | ".join(parts)
    path = _log_path(bot_id)
    with path.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    logger.info("[%s] %s", bot_id, line)


def log_evaluation(
    bot_id: str,
    candle: dict[str, Any],
    fast: float,
    slow: float,
    cross: str | None,
) -> None:
    log_decision(
        bot_id,
        "evaluate",
        candle_close=float(candle["close"]),
        sma_fast=fast,
        sma_slow=slow,
        extra=f"granularity={candle.get('granularity')} cross={cross or 'none'}",
    )
