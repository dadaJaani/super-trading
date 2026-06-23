"""High-visibility console lines for trade open/close events."""

from __future__ import annotations

import logging

logger = logging.getLogger("trade.console")


def log_trade_console(
    action: str,
    bot_id: str,
    instrument: str,
    direction: str,
    units: int,
    price: float,
    *,
    pnl: float | None = None,
    trade_id: str | None = None,
) -> None:
    """Print a grep-friendly TRADE line to the trading terminal."""
    parts = [
        f"TRADE {action.upper():5}",
        f"bot={bot_id}",
        instrument,
        direction,
        f"{units}u",
        f"@ {price:.2f}",
    ]
    if pnl is not None:
        sign = "+" if pnl >= 0 else ""
        parts.append(f"pnl={sign}{pnl:.2f}")
    if trade_id:
        parts.append(f"trade_id={trade_id}")

    line = "  ".join(parts)
    logger.info(line)
    print(line, flush=True)
