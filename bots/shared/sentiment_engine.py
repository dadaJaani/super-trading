"""LLM sentiment scoring via Claude API."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class SentimentEngine:
    """Subscribes to news:raw, scores headlines, publishes to news:scored."""

    INPUT_CHANNEL = "news:raw"
    OUTPUT_CHANNEL = "news:scored"

    def start(self) -> None:
        logger.info("SentimentEngine started (stub)")

    def stop(self) -> None:
        logger.info("SentimentEngine stopped")

    def score_headline(self, headline: str, instrument: str = "XAU_USD") -> float:
        """Return sentiment score from -1.0 to +1.0."""
        logger.debug("Scoring headline (stub): %s", headline)
        return 0.0
