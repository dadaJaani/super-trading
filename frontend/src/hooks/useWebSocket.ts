import { useEffect } from 'react';
import { io, Socket } from 'socket.io-client';
import { useTradingStore, type CandlePoint } from '../store/tradingStore';

const WS_URL = import.meta.env.VITE_WS_URL ?? 'http://localhost:3210';
const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:3210';

export function useWebSocket() {
  const setWsConnected = useTradingStore((s) => s.setWsConnected);
  const updateBotState = useTradingStore((s) => s.updateBotState);
  const appendBalancePoint = useTradingStore((s) => s.appendBalancePoint);
  const appendCandle = useTradingStore((s) => s.appendCandle);
  const setLivePrice = useTradingStore((s) => s.setLivePrice);
  const setOpenTrades = useTradingStore((s) => s.setOpenTrades);
  const setSignals = useTradingStore((s) => s.setSignals);
  const selectedBotId = useTradingStore((s) => s.selectedBotId);
  const bots = useTradingStore((s) => s.bots);

  const selectedBot = bots.find((b) => b.id === selectedBotId);
  const chartGranularity = String(selectedBot?.config?.granularity ?? 'M5');
  const chartInstrument = selectedBot?.instrument ?? 'XAU_USD';

  const refreshOpenTrades = (botId: string) => {
    fetch(`${API_URL}/api/bots/${botId}/trades?status=open`)
      .then((res) => res.json())
      .then(setOpenTrades)
      .catch(console.error);
  };

  const refreshSignals = (botId: string) => {
    fetch(`${API_URL}/api/bots/${botId}/signals?limit=50`)
      .then((res) => res.json())
      .then(setSignals)
      .catch(console.error);
  };

  useEffect(() => {
    const socket: Socket = io(WS_URL, {
      transports: ['websocket'],
    });

    socket.on('connect', () => setWsConnected(true));
    socket.on('disconnect', () => setWsConnected(false));

    socket.on('bot:state', (payload: { channel?: string; data?: Record<string, unknown> }) => {
      const botId = payload.channel?.split(':').pop();
      const data = payload.data;
      if (botId && data) {
        const openTradeRaw = data.openTrade as Record<string, unknown> | null | undefined;
        updateBotState(botId, {
          pnl: Number(data.pnl ?? 0),
          openTrade: openTradeRaw
            ? {
                direction: String(openTradeRaw.direction ?? ''),
                units: Number(openTradeRaw.units ?? 0),
                openPrice: Number(openTradeRaw.openPrice ?? 0),
                currentPrice: Number(openTradeRaw.currentPrice ?? 0),
                pnl: Number(openTradeRaw.pnl ?? 0),
              }
            : null,
          lastSignal: data.lastSignal as Parameters<typeof updateBotState>[1]['lastSignal'],
        });
      }
    });

    socket.on('balance:update', (payload: { data?: Record<string, unknown> }) => {
      const data = payload.data;
      if (!data) return;
      appendBalancePoint({
        time: String(data.time ?? new Date().toISOString()),
        balance: Number(data.balance ?? 0),
        nav: Number(data.nav ?? data.balance ?? 0),
      });
    });

    socket.on('price:update', (payload: { data?: Record<string, unknown> }) => {
      const data = payload.data;
      if (data?.price != null && data.instrument === chartInstrument) {
        setLivePrice(Number(data.price));
      }
    });

    socket.on('candle:close', (payload: { data?: Record<string, unknown> }) => {
      const data = payload.data;
      if (!data) return;
      if (data.instrument !== chartInstrument || data.granularity !== chartGranularity) {
        return;
      }
      const candle: CandlePoint = {
        time: String(data.time ?? ''),
        instrument: String(data.instrument ?? 'XAU_USD'),
        granularity: String(data.granularity ?? 'M5'),
        open: Number(data.open ?? 0),
        high: Number(data.high ?? 0),
        low: Number(data.low ?? 0),
        close: Number(data.close ?? 0),
        volume: Number(data.volume ?? 0),
      };
      appendCandle(candle);
    });

    socket.on('signal:generated', () => {
      if (selectedBotId) refreshSignals(selectedBotId);
    });

    socket.on('trade:opened', () => {
      if (selectedBotId) refreshOpenTrades(selectedBotId);
    });

    socket.on('trade:closed', () => {
      if (selectedBotId) refreshOpenTrades(selectedBotId);
    });

    return () => {
      socket.disconnect();
    };
  }, [
    appendBalancePoint,
    appendCandle,
    chartGranularity,
    chartInstrument,
    selectedBotId,
    setLivePrice,
    setOpenTrades,
    setSignals,
    setWsConnected,
    updateBotState,
  ]);
}
