"""System diagnostics for SMA bots and market data."""

from __future__ import annotations

import sys
from pathlib import Path

from shared.db import get_connection, ping as db_ping
from shared.oanda_client import OandaClient
from strategies.sma_cross_bot import sma

INSTRUMENT = "XAU_USD"
LOG_DIR = Path(__file__).resolve().parents[1] / "logs"


def _tail_log(bot_id: str, lines: int = 5) -> list[str]:
    path = LOG_DIR / f"{bot_id}.log"
    if not path.exists():
        return [f"(no log file at {path})"]
    content = path.read_text(encoding="utf-8").strip().splitlines()
    return content[-lines:] if content else ["(empty log)"]


def _sma_preview(granularity: str, fast: int, slow: int) -> None:
    client = OandaClient()
    candles = client.get_candles(INSTRUMENT, granularity=granularity, count=max(50, slow + 5))
    closes = [c["close"] for c in candles]
    if len(closes) < slow + 1:
        print(f"  {granularity}: need more candles ({len(closes)})")
        return

    prev = closes[:-1]
    fast_prev = sma(prev, fast)
    slow_prev = sma(prev, slow)
    fast_now = sma(closes, fast)
    slow_now = sma(closes, slow)
    cross_up = fast_prev is not None and slow_prev is not None and fast_prev <= slow_prev and fast_now > slow_now
    cross_down = fast_prev is not None and slow_prev is not None and fast_prev >= slow_prev and fast_now < slow_now

    print(f"  {granularity}: close={closes[-1]:.2f} sma{fast}={fast_now:.2f} sma{slow}={slow_now:.2f}")
    if cross_up:
        print(f"    -> cross UP would fire LONG on next completed bar")
    elif cross_down:
        print(f"    -> cross DOWN would fire SHORT on next completed bar")
    else:
        print(f"    -> no cross on last bar (HOLD)")


def main() -> int:
    print("=== Super Trading diagnose ===\n")

    if not db_ping():
        print("FAIL: cannot connect to PostgreSQL — run `make up`")
        return 1
    print("PASS: PostgreSQL connected")

    try:
        client = OandaClient()
        account = client.get_account_summary()
        print(f"PASS: OANDA balance=${float(account.get('balance', 0)):.2f}")
    except Exception as exc:
        print(f"FAIL: OANDA — {exc}")
        return 1

    with get_connection() as conn:
        for gran in ("M5", "H1"):
            row = conn.execute(
                "SELECT COUNT(*) FROM candles WHERE instrument = %s AND granularity = %s",
                (INSTRUMENT, gran),
            ).fetchone()
            count = row[0] if row else 0
            status = "PASS" if count >= 50 else "WARN"
            print(f"{status}: candles {INSTRUMENT} {gran} count={count} (expect >= 50 after bots start)")

        for bot_id in ("gold_sma_m5_v1", "gold_sma_v1"):
            sig = conn.execute(
                "SELECT COUNT(*) FROM signals WHERE bot_id = %s",
                (bot_id,),
            ).fetchone()[0]
            trades = conn.execute(
                "SELECT COUNT(*) FROM trades WHERE bot_id = %s",
                (bot_id,),
            ).fetchone()[0]
            cfg = conn.execute("SELECT config FROM bots WHERE id = %s", (bot_id,)).fetchone()
            execute = dict(cfg[0]).get("execute_trades", True) if cfg and cfg[0] else "?"
            print(f"  {bot_id}: signals={sig} trades={trades} execute_trades={execute}")

    print("\nSMA preview (from OANDA, not DB):")
    _sma_preview("M5", 9, 21)
    _sma_preview("H1", 9, 21)

    print("\nLast log lines (gold_sma_m5_v1):")
    for line in _tail_log("gold_sma_m5_v1"):
        print(f"  {line}")

    print("\nIf candle counts are low, ensure `make dev-bots` is running.")
    print("M5 evaluates every ~5 min; trades only on SMA crossover (can be hours in a trend).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
