"""Load and serve ML models."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parents[1] / "ml" / "models"


class ModelRegistry:
    """Loads trained model files and exposes predict()."""

    def __init__(self) -> None:
        self._models: dict[str, Any] = {}

    def load(self, model_id: str) -> None:
        logger.info("Loading model %s (stub)", model_id)
        self._models[model_id] = None

    def predict(self, model_id: str, features: dict[str, Any]) -> dict[str, Any]:
        """Return direction and confidence."""
        logger.debug("Predict (stub) model=%s features=%s", model_id, features)
        return {"direction": "LONG", "confidence": 0.0}

    def reload(self, model_id: str) -> None:
        logger.info("Reloading model %s (stub)", model_id)
        self.load(model_id)
