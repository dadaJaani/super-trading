"""Load bot and broker account definitions from JSON config files."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from strategies.gold_sma_m5_v1 import GoldSmaM5Bot
from strategies.gold_sma_v1 import GoldSmaBot
from strategies.sma_cross_bot import SmaCrossBot

logger = logging.getLogger(__name__)

CONFIG_ROOT = Path(__file__).resolve().parents[1] / "config"
ACCOUNTS_FILE = CONFIG_ROOT / "accounts.json"
ACCOUNTS_LOCAL_FILE = CONFIG_ROOT / "accounts.local.json"
BOTS_DIR = CONFIG_ROOT / "bots"

STRATEGY_CLASSES: dict[str, type[SmaCrossBot]] = {
    "gold_sma_v1": GoldSmaBot,
    "gold_sma_m5_v1": GoldSmaM5Bot,
}


@dataclass
class BrokerAccountDef:
    ref: str
    broker: str
    env: str | None = None
    api_key_env: str | None = None
    account_id_env: str | None = None
    enabled: bool = True


@dataclass
class ResolvedBrokerAccount:
    ref: str
    broker: str
    env: str
    api_key: str
    account_id: str


@dataclass
class BotConfig:
    id: str
    title: str
    description: str
    account: str
    strategy: str
    instrument: str
    enabled: bool
    params: dict[str, Any] = field(default_factory=dict)


class BotRegistry:
    """Loads accounts + bot JSON configs and instantiates trading bots."""

    def __init__(
        self,
        accounts: dict[str, BrokerAccountDef],
        bots: list[BotConfig],
    ) -> None:
        self.accounts = accounts
        self.bots = bots

    @classmethod
    def load(cls) -> BotRegistry:
        accounts = _load_accounts()
        bots = _load_bots(accounts)
        _validate(accounts, bots)
        return cls(accounts, bots)

    def enabled_bots(self) -> list[BotConfig]:
        return [b for b in self.bots if b.enabled]

    def resolve_account(self, account_ref: str) -> ResolvedBrokerAccount:
        defn = self.accounts.get(account_ref)
        if defn is None:
            raise ValueError(f"Unknown account ref: {account_ref}")

        if defn.broker == "interactive_brokers":
            raise NotImplementedError(
                f"Interactive Brokers account {account_ref} is not implemented yet"
            )

        if defn.broker != "oanda":
            raise ValueError(f"Unsupported broker {defn.broker!r} for account {account_ref}")

        if not defn.api_key_env or not defn.account_id_env:
            raise ValueError(
                f"Account {account_ref} missing api_key_env or account_id_env in config"
            )

        api_key = os.environ.get(defn.api_key_env, "").strip()
        account_id = os.environ.get(defn.account_id_env, "").strip()
        if not api_key or not account_id:
            raise ValueError(
                f"Account {account_ref} requires env vars "
                f"{defn.api_key_env} and {defn.account_id_env} to be set"
            )

        env = (defn.env or "practice").lower()
        if env not in ("practice", "live"):
            raise ValueError(f"Account {account_ref} env must be 'practice' or 'live'")

        return ResolvedBrokerAccount(
            ref=account_ref,
            broker=defn.broker,
            env=env,
            api_key=api_key,
            account_id=account_id,
        )

    def instantiate_bots(
        self,
        redis: Any,
        clients: dict[str, Any],
    ) -> list[SmaCrossBot]:
        instances: list[SmaCrossBot] = []
        for cfg in self.enabled_bots():
            if cfg.strategy not in STRATEGY_CLASSES:
                logger.warning(
                    "Skipping bot %s — strategy %s not registered",
                    cfg.id,
                    cfg.strategy,
                )
                continue

            client = clients.get(cfg.account)
            if client is None:
                logger.error("No broker client for account %s (bot %s)", cfg.account, cfg.id)
                continue

            bot_cls = STRATEGY_CLASSES[cfg.strategy]
            bot = bot_cls(redis=redis, oanda=client)
            bot.id = cfg.id
            bot.instrument = cfg.instrument
            bot._bot_params = dict(cfg.params)  # noqa: SLF001
            instances.append(bot)
            logger.info("Instantiated bot %s (%s) on account %s", cfg.id, cfg.strategy, cfg.account)

        return instances

    def account_stream_specs(self) -> dict[str, dict[str, set[str]]]:
        """Per account_ref: sets of instruments and granularities from enabled bots."""
        specs: dict[str, dict[str, set[str]]] = {}
        for cfg in self.enabled_bots():
            if cfg.strategy not in STRATEGY_CLASSES:
                continue
            entry = specs.setdefault(cfg.account, {"instruments": set(), "granularities": set()})
            entry["instruments"].add(cfg.instrument)
            granularity = str(cfg.params.get("granularity", "H1"))
            entry["granularities"].add(granularity)
        return specs

    def account_instruments(self) -> dict[str, set[str]]:
        """Per account_ref: instruments needed for price polling."""
        result: dict[str, set[str]] = {}
        for cfg in self.enabled_bots():
            if cfg.strategy not in STRATEGY_CLASSES:
                continue
            result.setdefault(cfg.account, set()).add(cfg.instrument)
        return result


class BrokerClientFactory:
    """Cached OANDA clients per account ref."""

    def __init__(self, registry: BotRegistry) -> None:
        self._registry = registry
        self._oanda_clients: dict[str, Any] = {}

    def build_clients_for_enabled_bots(self) -> dict[str, Any]:
        clients: dict[str, Any] = {}
        for cfg in self._registry.enabled_bots():
            if cfg.strategy not in STRATEGY_CLASSES:
                continue
            if cfg.account not in clients:
                clients[cfg.account] = self.get_oanda_client(cfg.account)
        return clients

    def get_oanda_client(self, account_ref: str) -> Any:
        if account_ref in self._oanda_clients:
            return self._oanda_clients[account_ref]

        from shared.oanda_client import OandaClient

        resolved = self._registry.resolve_account(account_ref)
        client = OandaClient(
            api_key=resolved.api_key,
            account_id=resolved.account_id,
            env=resolved.env,
            account_ref=account_ref,
        )
        self._oanda_clients[account_ref] = client
        return client


def _load_accounts() -> dict[str, BrokerAccountDef]:
    data = _read_json(ACCOUNTS_FILE)
    if ACCOUNTS_LOCAL_FILE.exists():
        local = _read_json(ACCOUNTS_LOCAL_FILE)
        data = _deep_merge(data, local)

    raw = data.get("accounts", {})
    accounts: dict[str, BrokerAccountDef] = {}
    for ref, item in raw.items():
        accounts[ref] = BrokerAccountDef(
            ref=ref,
            broker=str(item.get("broker", "")),
            env=item.get("env"),
            api_key_env=item.get("api_key_env"),
            account_id_env=item.get("account_id_env"),
            enabled=bool(item.get("enabled", True)),
        )
    return accounts


def _load_bots(accounts: dict[str, BrokerAccountDef]) -> list[BotConfig]:
    if not BOTS_DIR.is_dir():
        raise FileNotFoundError(f"Bot config directory not found: {BOTS_DIR}")

    bots: list[BotConfig] = []
    for path in sorted(BOTS_DIR.glob("*.json")):
        item = _read_json(path)
        account_ref = str(item.get("account", ""))
        if account_ref not in accounts:
            raise ValueError(f"Bot {path.name} references unknown account {account_ref}")

        bots.append(
            BotConfig(
                id=str(item["id"]),
                title=str(item.get("title", item["id"])),
                description=str(item.get("description", "")),
                account=account_ref,
                strategy=str(item.get("strategy", item["id"])),
                instrument=str(item.get("instrument", "XAU_USD")),
                enabled=bool(item.get("enabled", False)),
                params=dict(item.get("params", {})),
            )
        )
    return bots


def _validate(accounts: dict[str, BrokerAccountDef], bots: list[BotConfig]) -> None:
    seen: set[str] = set()
    for bot in bots:
        if bot.id in seen:
            raise ValueError(f"Duplicate bot id: {bot.id}")
        seen.add(bot.id)

    for bot in bots:
        if not bot.enabled:
            continue
        account = accounts[bot.account]
        if not account.enabled:
            raise ValueError(f"Bot {bot.id} uses disabled account {bot.account}")
        if account.broker == "interactive_brokers":
            raise NotImplementedError(
                f"Bot {bot.id} uses IB account {bot.account} — not implemented"
            )


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result
