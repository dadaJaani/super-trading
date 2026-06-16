interface TradeChartProps {
  instrument: string;
}

export function TradeChart({ instrument }: TradeChartProps) {
  return (
    <div className="flex h-64 items-center justify-center rounded-lg border border-slate-700 bg-slate-950">
      <div className="text-center text-slate-500">
        <p className="text-sm">Price chart placeholder</p>
        <p className="mt-1 font-mono text-xs">{instrument}</p>
      </div>
    </div>
  );
}
