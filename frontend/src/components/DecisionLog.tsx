import { useEffect } from 'react';
import { useTradingStore } from '../store/tradingStore';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:3210';

interface DecisionLogProps {
  botId: string | null;
}

function directionClass(direction: string | null): string {
  if (direction === 'LONG') return 'text-emerald-400';
  if (direction === 'SHORT') return 'text-red-400';
  if (direction === 'HOLD') return 'text-slate-400';
  return 'text-slate-200';
}

export function DecisionLog({ botId }: DecisionLogProps) {
  const signals = useTradingStore((s) => s.signals);
  const setSignals = useTradingStore((s) => s.setSignals);

  useEffect(() => {
    if (!botId) {
      setSignals([]);
      return;
    }

    const load = () => {
      fetch(`${API_URL}/api/bots/${botId}/signals?limit=50`)
        .then((res) => res.json())
        .then(setSignals)
        .catch(console.error);
    };

    load();
    const interval = setInterval(load, 10000);
    return () => clearInterval(interval);
  }, [botId, setSignals]);

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
      <h3 className="mb-3 text-sm font-medium text-slate-300">Decision Log</h3>
      {signals.length === 0 ? (
        <p className="text-sm text-slate-500">
          No evaluations yet — wait for next M5/H1 candle close (~5 min for M5).
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs text-slate-500">
                <th className="pb-2 pr-3">Time</th>
                <th className="pb-2 pr-3">Signal</th>
                <th className="pb-2 pr-3">SMA fast</th>
                <th className="pb-2 pr-3">SMA slow</th>
                <th className="pb-2 pr-3">Cross</th>
                <th className="pb-2">Acted</th>
              </tr>
            </thead>
            <tbody>
              {signals.map((row) => {
                const features = row.mlFeatures ?? {};
                const smaFast = features.sma_fast as number | undefined;
                const smaSlow = features.sma_slow as number | undefined;
                const cross = features.cross as string | undefined;
                return (
                  <tr key={row.id} className="border-t border-slate-800 text-slate-200">
                    <td className="py-2 pr-3 font-mono text-xs text-slate-400">
                      {row.time ? new Date(row.time).toLocaleString() : '—'}
                    </td>
                    <td className={`py-2 pr-3 font-medium ${directionClass(row.direction)}`}>
                      {row.direction ?? '—'}
                    </td>
                    <td className="py-2 pr-3 font-mono">
                      {smaFast != null ? smaFast.toFixed(2) : '—'}
                    </td>
                    <td className="py-2 pr-3 font-mono">
                      {smaSlow != null ? smaSlow.toFixed(2) : '—'}
                    </td>
                    <td className="py-2 pr-3">{cross ?? '—'}</td>
                    <td className="py-2">{row.actedOn ? 'yes' : 'no'}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-2 text-xs text-slate-500">
        File log: bots/logs/{botId ?? 'bot'}.log
      </p>
    </div>
  );
}
