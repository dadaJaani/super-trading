"""Export completed candles from Postgres to Parquet for ML training."""

from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from shared.db import get_connection

logger = logging.getLogger(__name__)

DEFAULT_DATA_ROOT = Path(__file__).resolve().parents[2] / "data" / "candles"


def fetch_candles(
    instrument: str,
    granularity: str,
    since: datetime | None = None,
) -> list[dict[str, object]]:
    query = """
        SELECT time, instrument, granularity, open, high, low, close, volume
        FROM candles
        WHERE instrument = %s AND granularity = %s
    """
    params: list[object] = [instrument, granularity]
    if since is not None:
        query += " AND time >= %s"
        params.append(since)
    query += " ORDER BY time ASC"

    with get_connection() as conn:
        rows = conn.execute(query, params).fetchall()

    return [
        {
            "time": row[0],
            "instrument": row[1],
            "granularity": row[2],
            "open": float(row[3]),
            "high": float(row[4]),
            "low": float(row[5]),
            "close": float(row[6]),
            "volume": int(row[7]),
        }
        for row in rows
    ]


def export_to_parquet(
    instrument: str,
    granularity: str,
    output_dir: Path | None = None,
    since: datetime | None = None,
) -> Path:
    rows = fetch_candles(instrument, granularity, since=since)
    if not rows:
        raise ValueError(
            f"No candles for {instrument} {granularity} — "
            "ensure run-trading has been collecting data"
        )

    root = output_dir or DEFAULT_DATA_ROOT
    out_path = root / instrument / granularity / "candles.parquet"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    table = pa.Table.from_pylist(rows)
    pq.write_table(table, out_path)

    logger.info(
        "Exported %d rows to %s (%s %s)",
        len(rows),
        out_path,
        instrument,
        granularity,
    )
    return out_path


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Export Postgres candles to Parquet")
    parser.add_argument("--instrument", required=True, help="e.g. XAU_USD")
    parser.add_argument("--granularity", required=True, help="e.g. M5, M30, H1")
    parser.add_argument(
        "--since",
        default=None,
        help="ISO timestamp — export bars on or after this time",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Root output dir (default: bots/data/candles)",
    )
    args = parser.parse_args()

    since = datetime.fromisoformat(args.since) if args.since else None
    output_dir = Path(args.output_dir) if args.output_dir else None

    try:
        path = export_to_parquet(
            args.instrument,
            args.granularity,
            output_dir=output_dir,
            since=since,
        )
        print(f"Exported to {path}")
        return 0
    except ValueError as exc:
        logger.error("%s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
