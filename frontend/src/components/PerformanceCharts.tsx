import type { PerformanceSummary } from '../store/tradingStore';

interface PerformanceChartsProps {
  performance: PerformanceSummary | null;
}

export function PerformanceCharts({ performance }: PerformanceChartsProps) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
      <h3 className="mb-3 text-sm font-medium text-slate-300">Performance</h3>
      {performance ? (
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div
              className={`font-mono text-lg ${performance.totalPnl >= 0 ? 'text-emerald-400' : 'text-red-400'}`}
            >
              ${performance.totalPnl.toFixed(2)}
            </div>
            <div className="text-xs text-slate-500">Total P&L</div>
          </div>
          <div>
            <div className="font-mono text-lg text-slate-200">
              {performance.closedTrades}
            </div>
            <div className="text-xs text-slate-500">Closed Trades</div>
          </div>
          <div>
            <div className="font-mono text-lg text-slate-200">
              {(performance.winRate * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-slate-500">Win Rate</div>
          </div>
        </div>
      ) : (
        <p className="text-sm text-slate-500">No performance data yet.</p>
      )}
    </div>
  );
}
