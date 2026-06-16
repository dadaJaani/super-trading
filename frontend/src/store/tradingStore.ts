import { create } from 'zustand';

export interface Bot {
  id: string;
  name: string | null;
  instrument: string | null;
  strategy: string | null;
  status: string | null;
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

export interface NewsItem {
  id: string;
  headline: string;
  sentimentScore: number;
  time: string;
  source?: string;
}

export interface PerformanceSummary {
  totalPnl: number;
  closedTrades: number;
  winRate: number;
}

interface TradingState {
  bots: Bot[];
  selectedBotId: string | null;
  botStates: Record<string, BotState>;
  news: NewsItem[];
  performance: PerformanceSummary | null;
  wsConnected: boolean;
  setBots: (bots: Bot[]) => void;
  selectBot: (id: string | null) => void;
  updateBotState: (botId: string, state: Partial<BotState>) => void;
  addNews: (item: NewsItem) => void;
  setPerformance: (performance: PerformanceSummary) => void;
  setWsConnected: (connected: boolean) => void;
}

export const useTradingStore = create<TradingState>((set) => ({
  bots: [],
  selectedBotId: null,
  botStates: {},
  news: [],
  performance: null,
  wsConnected: false,
  setBots: (bots) =>
    set({
      bots,
      selectedBotId: bots[0]?.id ?? null,
    }),
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
  addNews: (item) =>
    set((prev) => ({
      news: [item, ...prev.news].slice(0, 100),
    })),
  setPerformance: (performance) => set({ performance }),
  setWsConnected: (connected) => set({ wsConnected: connected }),
}));
