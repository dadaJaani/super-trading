import { useEffect } from 'react';
import { io, Socket } from 'socket.io-client';
import { useTradingStore } from '../store/tradingStore';

const WS_URL = import.meta.env.VITE_WS_URL ?? 'http://localhost:3001';

export function useWebSocket() {
  const setWsConnected = useTradingStore((s) => s.setWsConnected);
  const updateBotState = useTradingStore((s) => s.updateBotState);
  const addNews = useTradingStore((s) => s.addNews);

  useEffect(() => {
    const socket: Socket = io(WS_URL, {
      transports: ['websocket'],
    });

    socket.on('connect', () => setWsConnected(true));
    socket.on('disconnect', () => setWsConnected(false));

    socket.on('bot:state', (payload: { channel?: string; data?: Record<string, unknown> }) => {
      const botId = payload.channel?.split(':').pop();
      if (botId && payload.data) {
        updateBotState(botId, payload.data as Parameters<typeof updateBotState>[1]);
      }
    });

    socket.on('news:scored', (payload: { data?: Record<string, unknown> }) => {
      const data = payload.data as Record<string, unknown> | undefined;
      if (data?.headline) {
        addNews({
          id: String(data.id ?? crypto.randomUUID()),
          headline: String(data.headline),
          sentimentScore: Number(data.sentiment_score ?? data.sentimentScore ?? 0),
          time: String(data.time ?? new Date().toISOString()),
          source: data.source ? String(data.source) : undefined,
        });
      }
    });

    return () => {
      socket.disconnect();
    };
  }, [addNews, setWsConnected, updateBotState]);
}
