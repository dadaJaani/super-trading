"""Gold SMA M5 test bot — faster crossover signals for dev/testing."""

from strategies.sma_cross_bot import SmaCrossBot


class GoldSmaM5Bot(SmaCrossBot):
    id = "gold_sma_m5_v1"
    instrument = "XAU_USD"
