import type { Signal } from '../store/tradingStore';

interface SignalPanelProps {
  signal: Signal | null;
}

export function SignalPanel({ signal }: SignalPanelProps) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
      <h3 className="mb-2 text-sm font-medium text-slate-300">Latest Signal</h3>
      {signal ? (
        <div className="space-y-1 text-sm">
          <div className="font-mono text-emerald-400">
            {signal.direction} | Confidence: {signal.confidence.toFixed(2)}
          </div>
          {signal.trigger && (
            <div className="text-slate-400">Trigger: {signal.trigger}</div>
          )}
        </div>
      ) : (
        <p className="text-sm text-slate-500">Waiting for signals...</p>
      )}
    </div>
  );
}
