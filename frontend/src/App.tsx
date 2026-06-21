import { useEffect, useState } from 'react';
import { BotDetail } from './components/BotDetail';
import { BotList } from './components/BotList';
import { useWebSocket } from './hooks/useWebSocket';
import { useTradingStore } from './store/tradingStore';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:3210';

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
  const performance = useTradingStore((s) => s.performance);
  const balanceHistory = useTradingStore((s) => s.balanceHistory);
  const livePrice = useTradingStore((s) => s.livePrice);
  const wsConnected = useTradingStore((s) => s.wsConnected);
  const setBots = useTradingStore((s) => s.setBots);
  const setPerformance = useTradingStore((s) => s.setPerformance);
  const setBalanceHistory = useTradingStore((s) => s.setBalanceHistory);

  useEffect(() => {
    fetch(`${API_URL}/api/bots`)
      .then((res) => res.json())
      .then(setBots)
      .catch(console.error);

    fetch(`${API_URL}/api/performance`)
      .then((res) => res.json())
      .then(setPerformance)
      .catch(console.error);

    fetch(`${API_URL}/api/performance/balance`)
      .then((res) => res.json())
      .then((rows) =>
        setBalanceHistory(
          rows.map((r: { time: string; balance: number; nav: number }) => ({
            time: r.time,
            balance: Number(r.balance),
            nav: Number(r.nav),
          })),
        ),
      )
      .catch(console.error);
  }, [setBots, setPerformance, setBalanceHistory]);

  const selectedBot = bots.find((b) => b.id === selectedBotId);
  const selectedState = selectedBotId ? botStates[selectedBotId] : undefined;

  const headerBalance =
    performance?.latestBalance?.balance ??
    balanceHistory[balanceHistory.length - 1]?.balance ??
    0;

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b border-slate-700 bg-slate-900 px-6 py-4">
        <div>
          <h1 className="text-lg font-semibold text-slate-100">Gold SMA Trading</h1>
          <div className="mt-1 flex items-center gap-2 text-xs text-slate-400">
            <span
              className={`h-2 w-2 rounded-full ${wsConnected ? 'bg-emerald-500' : 'bg-red-500'}`}
            />
            {wsConnected ? 'Connected' : 'Disconnected'}
          </div>
        </div>
        <div className="flex items-center gap-6">
          {livePrice != null && (
            <div className="text-right">
              <div className="text-xs text-slate-500">XAU/USD</div>
              <div className="font-mono text-sm text-emerald-400">${livePrice.toFixed(2)}</div>
            </div>
          )}
          <div className="text-right">
            <div className="text-xs text-slate-500">Account Balance</div>
            <div className="font-mono text-sm text-slate-100">${headerBalance.toFixed(2)}</div>
          </div>
          <LiveClock />
        </div>
      </header>

      <main className="grid flex-1 grid-cols-1 gap-4 p-4 lg:grid-cols-[280px_1fr]">
        <aside>
          <h2 className="mb-3 text-sm font-medium text-slate-400">SMA Bots</h2>
          <BotList bots={bots} />
        </aside>

        <section className="space-y-4">
          <BotDetail bot={selectedBot} botState={selectedState} />
        </section>
      </main>
    </div>
  );
}

export default App;
