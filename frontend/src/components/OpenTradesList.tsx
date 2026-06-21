import { useEffect } from 'react';
import { useTradingStore, type TradeRecord } from '../store/tradingStore';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:3210';

interface OpenTradesListProps {
  botId: string | null;
}

export function OpenTradesList({ botId }: OpenTradesListProps) {
  const openTrades = useTradingStore((s) => s.openTrades);
  const setOpenTrades = useTradingStore((s) => s.setOpenTrades);
  const botState = useTradingStore((s) => (botId ? s.botStates[botId] : undefined));

  useEffect(() => {
    if (!botId) {
      setOpenTrades([]);
      return;
    }

    fetch(`${API_URL}/api/bots/${botId}/trades?status=open`)
      .then((res) => res.json())
      .then((rows: TradeRecord[]) => setOpenTrades(rows))
      .catch(console.error);
  }, [botId, setOpenTrades]);

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
      <h3 className="mb-3 text-sm font-medium text-slate-300">Open Trades</h3>
      {openTrades.length === 0 ? (
        <p className="text-sm text-slate-500">No open trades</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-xs text-slate-500">
                <th className="pb-2 pr-4">Instrument</th>
                <th className="pb-2 pr-4">Direction</th>
                <th className="pb-2 pr-4">Units</th>
                <th className="pb-2 pr-4">Open</th>
                <th className="pb-2">P&amp;L</th>
              </tr>
            </thead>
            <tbody>
              {openTrades.map((trade) => {
                const openPrice = Number(trade.openPrice ?? 0);
                const livePnl = botState?.openTrade?.pnl;
                const pnl = livePnl ?? Number(trade.pnl ?? 0);
                return (
                  <tr key={trade.id} className="border-t border-slate-800 text-slate-200">
                    <td className="py-2 pr-4 font-mono">{trade.instrument}</td>
                    <td className="py-2 pr-4">{trade.direction}</td>
                    <td className="py-2 pr-4 font-mono">{trade.units}</td>
                    <td className="py-2 pr-4 font-mono">${openPrice.toFixed(2)}</td>
                    <td
                      className={`py-2 font-mono ${pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
                    >
                      {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
