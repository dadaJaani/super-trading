"""Calculate indicators and label price spikes."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def build_features(input_path: str, output_path: str) -> None:
    logger.info("build_features (stub): %s -> %s", input_path, output_path)
