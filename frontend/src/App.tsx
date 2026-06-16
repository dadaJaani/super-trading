import { useEffect, useState } from 'react';
import { BotDetail } from './components/BotDetail';
import { BotList } from './components/BotList';
import { NewsFeed } from './components/NewsFeed';
import { PerformanceCharts } from './components/PerformanceCharts';
import { useWebSocket } from './hooks/useWebSocket';
import { useTradingStore } from './store/tradingStore';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:3001';

function LiveClock() {
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const interval = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <span className="font-mono text-sm text-slate-400">
      {time.toLocaleTimeString()}
    </span>
  );
}

function App() {
  useWebSocket();

  const bots = useTradingStore((s) => s.bots);
  const selectedBotId = useTradingStore((s) => s.selectedBotId);
  const botStates = useTradingStore((s) => s.botStates);
  const news = useTradingStore((s) => s.news);
  const performance = useTradingStore((s) => s.performance);
  const wsConnected = useTradingStore((s) => s.wsConnected);
  const setBots = useTradingStore((s) => s.setBots);
  const setPerformance = useTradingStore((s) => s.setPerformance);

  useEffect(() => {
    fetch(`${API_URL}/api/bots`)
      .then((res) => res.json())
      .then(setBots)
      .catch(console.error);

    fetch(`${API_URL}/api/performance`)
      .then((res) => res.json())
      .then(setPerformance)
      .catch(console.error);
  }, [setBots, setPerformance]);

  const selectedBot = bots.find((b) => b.id === selectedBotId);
  const selectedState = selectedBotId ? botStates[selectedBotId] : undefined;
  const totalPnl = Object.values(botStates).reduce((sum, s) => sum + (s.pnl ?? 0), 0);

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b border-slate-700 bg-slate-900 px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Super Trading</h1>
          <div className="mt-1 flex items-center gap-2 text-xs text-slate-400">
            <span
              className={`h-2 w-2 rounded-full ${wsConnected ? 'bg-emerald-500' : 'bg-red-500'}`}
            />
            {wsConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="text-right">
            <div className="text-xs text-slate-500">Total P&L</div>
            <div
              className={`font-mono text-sm ${totalPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
            >
              {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
            </div>
          </div>
          <LiveClock />
        </div>
      </header>

      <main className="grid flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-[280px_1fr]">
        <aside>
          <h2 className="mb-3 text-sm font-medium text-slate-400">Bots</h2>
          <BotList bots={bots} />
        </aside>

        <section className="space-y-4">
          <BotDetail bot={selectedBot} botState={selectedState} />
          <PerformanceCharts performance={performance} />
          <NewsFeed news={news} />
        </section>
      </main>
    </div>
  );
}

export default App;
