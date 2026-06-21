"""Gold SMA crossover bot — XAU/USD H1 SMA 9/21."""

from strategies.sma_cross_bot import SmaCrossBot


class GoldSmaBot(SmaCrossBot):
    id = "gold_sma_v1"
    instrument = "XAU_USD"
