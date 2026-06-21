import type { Bot } from '../store/tradingStore';
import { useTradingStore } from '../store/tradingStore';

function statusColor(status: string | null): string {
  switch (status) {
    case 'running':
      return 'bg-emerald-500';
    case 'error':
      return 'bg-red-500';
    case 'stopped':
      return 'bg-slate-500';
    default:
      return 'bg-slate-600';
  }
}

interface BotListProps {
  bots: Bot[];
}

export function BotList({ bots }: BotListProps) {
  const selectedBotId = useTradingStore((s) => s.selectedBotId);
  const botStates = useTradingStore((s) => s.botStates);
  const selectBot = useTradingStore((s) => s.selectBot);

  if (bots.length === 0) {
    return (
      <div className="rounded-lg border border-slate-700 bg-slate-900 p-4 text-sm text-slate-400">
        No bots registered yet.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {bots.map((bot) => {
        const pnl = botStates[bot.id]?.pnl ?? 0;
        const isSelected = bot.id === selectedBotId;

        return (
          <button
            key={bot.id}
            type="button"
            onClick={() => selectBot(bot.id)}
            className={`w-full rounded-lg border p-3 text-left transition ${
              isSelected
                ? 'border-emerald-500 bg-slate-800'
                : 'border-slate-700 bg-slate-900 hover:border-slate-500'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${statusColor(bot.status)}`} />
              <span className="font-medium text-slate-100">{bot.name ?? bot.id}</span>
            </div>
            {bot.description ? (
              <p className="mt-1 text-xs text-slate-400 line-clamp-2">{bot.description}</p>
            ) : null}
            <div className="mt-1 text-xs text-slate-500">{bot.instrument}</div>
            <div
              className={`mt-2 text-sm font-mono ${pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
            >
              P&L: {pnl >= 0 ? '+' : ''}${pnl.toFixed(2)}
            </div>
          </button>
        );
      })}
    </div>
  );
}
