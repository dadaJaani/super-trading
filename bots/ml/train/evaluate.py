"""Backtest and walk-forward evaluation."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def evaluate(model_path: str, test_data_path: str) -> dict:
    logger.info("evaluate (stub): model=%s data=%s", model_path, test_data_path)
    return {"accuracy": 0.0, "win_rate": 0.0}
