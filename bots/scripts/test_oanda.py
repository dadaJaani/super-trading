"""OANDA connectivity smoke test — read-only checks."""

from __future__ import annotations

import argparse
import sys

from shared.bot_registry import BotRegistry, BrokerClientFactory
from shared.oanda_client import OandaClient

INSTRUMENT = "XAU_USD"


def main() -> int:
    parser = argparse.ArgumentParser(description="OANDA connectivity test")
    parser.add_argument(
        "--account",
        default=None,
        help="Account ref from bots/config/accounts.json (e.g. oanda_paper_1)",
    )
    args = parser.parse_args()

    print("=== OANDA connectivity test ===\n")
    errors: list[str] = []

    try:
        if args.account:
            registry = BotRegistry.load()
            factory = BrokerClientFactory(registry)
            client = factory.get_oanda_client(args.account)
            print(f"Account ref: {args.account}\n")
        else:
            client = OandaClient()
    except (ValueError, NotImplementedError) as exc:
        print(f"FAIL: {exc}")
        return 1

    print(f"Environment: {client._api.environment}")
    print(f"Account ID:  {client.account_id}\n")

    try:
        account = client.get_account_summary()
        balance = float(account.get("balance", 0))
        nav = float(account.get("NAV", balance))
        print(f"PASS account summary — balance=${balance:.2f} NAV=${nav:.2f}")
    except Exception as exc:
        errors.append(f"account summary: {exc}")
        print(f"FAIL account summary — {exc}")

    try:
        price = client.get_latest_price(INSTRUMENT)
        if price is None:
            errors.append("latest price returned None")
            print("FAIL latest price — no data")
        else:
            print(f"PASS latest price — {INSTRUMENT}=${price:.2f}")
    except Exception as exc:
        errors.append(f"latest price: {exc}")
        print(f"FAIL latest price — {exc}")

    for granularity in ("M5", "H1"):
        try:
            candles = client.get_candles(INSTRUMENT, granularity=granularity, count=5)
            if not candles:
                errors.append(f"{granularity} candles empty")
                print(f"FAIL {granularity} candles — empty response")
            else:
                last = candles[-1]
                print(
                    f"PASS {granularity} candles — {len(candles)} bars, "
                    f"last close=${last['close']:.2f} @ {last['time']}"
                )
        except Exception as exc:
            errors.append(f"{granularity} candles: {exc}")
            print(f"FAIL {granularity} candles — {exc}")

    try:
        trades = client.get_open_trades()
        print(f"PASS open trades — {len(trades)} open")
        for t in trades:
            print(f"  · {t['instrument']} {t['direction']} {t['units']}u P&L=${t['unrealized_pl']:.2f}")
    except Exception as exc:
        errors.append(f"open trades: {exc}")
        print(f"FAIL open trades — {exc}")

    print()
    if errors:
        print(f"RESULT: {len(errors)} check(s) failed")
        return 1

    print("RESULT: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
