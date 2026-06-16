import type { Bot, BotState } from '../store/tradingStore';
import { SignalPanel } from './SignalPanel';
import { TradeChart } from './TradeChart';

interface BotDetailProps {
  bot: Bot | undefined;
  botState: BotState | undefined;
}

export function BotDetail({ bot, botState }: BotDetailProps) {
  if (!bot) {
    return (
      <div className="flex h-full items-center justify-center rounded-lg border border-slate-700 bg-slate-900 p-8 text-slate-400">
        Select a bot to view details
      </div>
    );
  }

  const openTrade = botState?.openTrade;

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold text-slate-100">{bot.name ?? bot.id}</h2>
        <p className="text-sm text-slate-400">
          {bot.instrument} · {bot.strategy} · {bot.status}
        </p>
      </div>

      <TradeChart instrument={bot.instrument ?? 'XAU_USD'} />

      <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
        <h3 className="mb-2 text-sm font-medium text-slate-300">Open Trade</h3>
        {openTrade ? (
          <div className="font-mono text-sm text-slate-200">
            {openTrade.direction} {openTrade.units} units @ ${openTrade.openPrice.toFixed(2)}
            <div className="mt-1 text-slate-400">
              Current: ${openTrade.currentPrice.toFixed(2)} | P&L:{' '}
              <span className={openTrade.pnl >= 0 ? 'text-emerald-400' : 'text-red-400'}>
                {openTrade.pnl >= 0 ? '+' : ''}${openTrade.pnl.toFixed(2)}
              </span>
            </div>
          </div>
        ) : (
          <p className="text-sm text-slate-500">No open trade</p>
        )}
      </div>

      <SignalPanel signal={botState?.lastSignal ?? null} />
    </div>
  );
}
