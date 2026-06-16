"""Train XGBoost / LSTM models."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def train(model_type: str = "xgboost", output_path: str = "ml/models/xgb_gold_v1.pkl") -> None:
    logger.info("train_model (stub): %s -> %s", model_type, output_path)
