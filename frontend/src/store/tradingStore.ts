import { create } from 'zustand';

export interface Bot {
  id: string;
  name: string | null;
  description: string | null;
  instrument: string | null;
  strategy: string | null;
  status: string | null;
  broker: string | null;
  accountRef: string | null;
  config: Record<string, unknown> | null;
  createdAt?: string;
}

export interface BotState {
  botId: string;
  pnl: number;
  openTrade: OpenTrade | null;
  lastSignal: Signal | null;
}

export interface OpenTrade {
  direction: string;
  units: number;
  openPrice: number;
  currentPrice: number;
  pnl: number;
}

export interface Signal {
  direction: string;
  confidence: number;
  trigger?: string;
  time?: string;
}

export interface PerformanceSummary {
  totalPnl: number;
  closedTrades: number;
  winRate: number;
  latestBalance?: {
    time: string;
    balance: number;
    nav: number;
  } | null;
}

export interface BalancePoint {
  time: string;
  balance: number;
  nav: number;
}

export interface CandlePoint {
  time: string;
  instrument: string;
  granularity: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface SignalRecord {
  id: string;
  botId: string;
  time: string | null;
  direction: string | null;
  confidence: string | null;
  actedOn: boolean;
  mlFeatures: Record<string, unknown> | null;
}

export interface TradeRecord {
  id: string;
  botId: string;
  oandaTradeId: string | null;
  instrument: string | null;
  direction: string | null;
  units: number | null;
  openPrice: string | null;
  closePrice: string | null;
  openTime: string | null;
  closeTime: string | null;
  pnl: string | null;
  status: string | null;
  unrealizedPnl?: number;
}

interface TradingState {
  bots: Bot[];
  selectedBotId: string | null;
  botStates: Record<string, BotState>;
  performance: PerformanceSummary | null;
  balanceHistory: BalancePoint[];
  candleHistory: CandlePoint[];
  livePrice: number | null;
  openTrades: TradeRecord[];
  signals: SignalRecord[];
  wsConnected: boolean;
  setBots: (bots: Bot[]) => void;
  selectBot: (id: string | null) => void;
  updateBotState: (botId: string, state: Partial<BotState>) => void;
  setPerformance: (performance: PerformanceSummary) => void;
  setBalanceHistory: (history: BalancePoint[]) => void;
  appendBalancePoint: (point: BalancePoint) => void;
  setCandleHistory: (candles: CandlePoint[]) => void;
  appendCandle: (candle: CandlePoint) => void;
  updateLastCandleClose: (close: number) => void;
  setLivePrice: (price: number) => void;
  setOpenTrades: (trades: TradeRecord[]) => void;
  setSignals: (signals: SignalRecord[]) => void;
  setWsConnected: (connected: boolean) => void;
}

export const useTradingStore = create<TradingState>((set) => ({
  bots: [],
  selectedBotId: null,
  botStates: {},
  performance: null,
  balanceHistory: [],
  candleHistory: [],
  livePrice: null,
  openTrades: [],
  signals: [],
  wsConnected: false,
  setBots: (bots) => {
    const smaBots = bots.filter((b) => b.id.startsWith('gold_sma'));
    const defaultId =
      smaBots.find((b) => b.id === 'gold_sma_m5_v1')?.id ?? smaBots[0]?.id ?? null;
    set({ bots: smaBots, selectedBotId: defaultId });
  },
  selectBot: (id) => set({ selectedBotId: id }),
  updateBotState: (botId, state) =>
    set((prev) => ({
      botStates: {
        ...prev.botStates,
        [botId]: {
          ...{
            botId,
            pnl: 0,
            openTrade: null,
            lastSignal: null,
          },
          ...prev.botStates[botId],
          ...state,
        },
      },
    })),
  setPerformance: (performance) => set({ performance }),
  setBalanceHistory: (history) => set({ balanceHistory: history }),
  appendBalancePoint: (point) =>
    set((prev) => ({
      balanceHistory: [...prev.balanceHistory, point].slice(-500),
    })),
  setCandleHistory: (candles) => set({ candleHistory: candles }),
  appendCandle: (candle) =>
    set((prev) => {
      const last = prev.candleHistory[prev.candleHistory.length - 1];
      if (
        last?.time === candle.time &&
        last.instrument === candle.instrument &&
        last.granularity === candle.granularity
      ) {
        const updated = [...prev.candleHistory];
        updated[updated.length - 1] = candle;
        return { candleHistory: updated };
      }
      return { candleHistory: [...prev.candleHistory, candle].slice(-200) };
    }),
  updateLastCandleClose: (close) =>
    set((prev) => {
      if (prev.candleHistory.length === 0) return prev;
      const updated = [...prev.candleHistory];
      const last = { ...updated[updated.length - 1], close };
      updated[updated.length - 1] = last;
      return { candleHistory: updated };
    }),
  setLivePrice: (price) => set({ livePrice: price }),
  setOpenTrades: (trades) => set({ openTrades: trades }),
  setSignals: (signals) => set({ signals }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
}));
