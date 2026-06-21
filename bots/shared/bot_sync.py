"""Sync bot JSON configs to the Postgres bots table."""

from __future__ import annotations

import json
import logging
from typing import Any

from shared.bot_registry import BotRegistry
from shared.db import get_connection

logger = logging.getLogger(__name__)


def sync_bots_to_db(registry: BotRegistry) -> None:
    for bot in registry.bots:
        account_def = registry.accounts[bot.account]
        config_payload: dict[str, Any] = {
            **bot.params,
            "account": bot.account,
            "broker": account_def.broker,
        }
        status = "running" if bot.enabled else "stopped"
        config_json = json.dumps(config_payload)

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO bots (
                    id, name, description, instrument, strategy, status,
                    broker, account_ref, config
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    instrument = EXCLUDED.instrument,
                    strategy = EXCLUDED.strategy,
                    status = EXCLUDED.status,
                    broker = EXCLUDED.broker,
                    account_ref = EXCLUDED.account_ref,
                    config = EXCLUDED.config
                """,
                (
                    bot.id,
                    bot.title,
                    bot.description,
                    bot.instrument,
                    bot.strategy,
                    status,
                    account_def.broker,
                    bot.account,
                    config_json,
                ),
            )
            conn.commit()

        logger.info("Synced bot %s (%s)", bot.id, status)
