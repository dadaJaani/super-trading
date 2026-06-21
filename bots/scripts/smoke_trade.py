"""Open and close a single paper trade to verify OANDA execution."""

from __future__ import annotations

import argparse
import sys
import time

from shared.oanda_client import OandaClient

INSTRUMENT = "XAU_USD"
UNITS = 1


def _extract_trade_id(response: dict) -> str | None:
    fill = response.get("orderFillTransaction") or {}
    trade_opened = fill.get("tradeOpened")
    if trade_opened:
        return str(trade_opened.get("tradeID"))
    return None


def _extract_pl(response: dict) -> float:
    fill = response.get("orderFillTransaction") or {}
    return float(fill.get("pl", 0))


def main() -> int:
    parser = argparse.ArgumentParser(description="OANDA paper trade smoke test")
    parser.add_argument(
        "--direction",
        choices=["long", "short"],
        default="long",
        help="Direction for test trade (default: long)",
    )
    parser.add_argument(
        "--account",
        default=None,
        help="Account ref from bots/config/accounts.json (e.g. oanda_paper_1)",
    )
    args = parser.parse_args()

    print("=== OANDA smoke trade ===\n")

    try:
        if args.account:
            from shared.bot_registry import BotRegistry, BrokerClientFactory

            registry = BotRegistry.load()
            factory = BrokerClientFactory(registry)
            client = factory.get_oanda_client(args.account)
            print(f"Account ref: {args.account}\n")
        else:
            client = OandaClient()
    except (ValueError, NotImplementedError) as exc:
        print(f"FAIL: {exc}")
        return 1

    units = UNITS if args.direction == "long" else -UNITS
    direction = "LONG" if units > 0 else "SHORT"

    existing = client.get_open_trade_for_instrument(INSTRUMENT)
    if existing:
        print(f"Closing existing {existing['direction']} trade {existing['oanda_trade_id']} first...")
        price = client.get_latest_price(INSTRUMENT) or existing["open_price"]
        close_resp = client.close_trade(existing["oanda_trade_id"])
        pnl = _extract_pl(close_resp)
        print(f"Closed — P&L=${pnl:.2f} @ ~${price:.2f}")

    print(f"Opening {direction} {abs(units)} unit on {INSTRUMENT}...")
    try:
        open_resp = client.create_market_order(INSTRUMENT, units)
        trade_id = _extract_trade_id(open_resp)
        if not trade_id:
            print(f"FAIL: no trade ID in response: {open_resp}")
            return 1
        print(f"PASS opened trade_id={trade_id}")
    except Exception as exc:
        print(f"FAIL open order — {exc}")
        return 1

    print("Waiting 3s...")
    time.sleep(3)

    price = client.get_latest_price(INSTRUMENT)
    print(f"Current price: ${price:.2f}" if price else "Current price: unknown")

    try:
        close_resp = client.close_trade(trade_id)
        pnl = _extract_pl(close_resp)
        print(f"PASS closed trade_id={trade_id} P&L=${pnl:.2f}")
    except Exception as exc:
        print(f"FAIL close order — {exc}")
        return 1

    print("\nRESULT: smoke trade completed — check OANDA practice UI")
    return 0


if __name__ == "__main__":
    sys.exit(main())
