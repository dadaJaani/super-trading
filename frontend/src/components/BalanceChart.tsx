import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTradingStore } from '../store/tradingStore';

export function BalanceChart() {
  const balanceHistory = useTradingStore((s) => s.balanceHistory);

  if (balanceHistory.length === 0) {
    return (
      <div className="flex h-64 items-center justify-center rounded-lg border border-slate-700 bg-slate-950">
        <p className="text-sm text-slate-500">No balance history yet</p>
      </div>
    );
  }

  const data = balanceHistory.map((point) => ({
    time: new Date(point.time).toLocaleString(),
    balance: point.balance,
    nav: point.nav,
  }));

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-950 p-4">
      <h3 className="mb-3 text-sm font-medium text-slate-300">Account Balance</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 10 }} minTickGap={40} />
            <YAxis
              tick={{ fill: '#94a3b8', fontSize: 10 }}
              domain={['auto', 'auto']}
              tickFormatter={(v) => `$${Number(v).toFixed(0)}`}
            />
            <Tooltip
              contentStyle={{ background: '#1e293b', border: '1px solid #475569' }}
              labelStyle={{ color: '#cbd5e1' }}
              formatter={(value) => [`$${Number(value).toFixed(2)}`, 'Balance']}
            />
            <Line
              type="monotone"
              dataKey="balance"
              stroke="#34d399"
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
