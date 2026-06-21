import { useEffect, useMemo, useRef } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useTradingStore } from '../store/tradingStore';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:3210';

function smaAt(closes: number[], period: number, index: number): number | null {
  if (index < period - 1) return null;
  const slice = closes.slice(index - period + 1, index + 1);
  return slice.reduce((sum, v) => sum + v, 0) / period;
}

interface PriceChartProps {
  instrument: string;
  granularity: string;
  fastPeriod?: number;
  slowPeriod?: number;
}

export function PriceChart({
  instrument,
  granularity,
  fastPeriod = 9,
  slowPeriod = 21,
}: PriceChartProps) {
  const candleHistory = useTradingStore((s) => s.candleHistory);
  const livePrice = useTradingStore((s) => s.livePrice);
  const setCandleHistory = useTradingStore((s) => s.setCandleHistory);
  const appendCandle = useTradingStore((s) => s.appendCandle);
  const setLivePrice = useTradingStore((s) => s.setLivePrice);
  const updateLastClose = useTradingStore((s) => s.updateLastCandleClose);
  const chartFilter = useRef({ instrument, granularity });

  chartFilter.current = { instrument, granularity };

  useEffect(() => {
    fetch(
      `${API_URL}/api/candles?instrument=${instrument}&granularity=${granularity}&limit=120`,
    )
      .then((res) => res.json())
      .then((rows) => {
        if (Array.isArray(rows)) {
          setCandleHistory(rows);
        }
      })
      .catch(console.error);
  }, [instrument, granularity, setCandleHistory]);

  useEffect(() => {
    const source = new EventSource(`${API_URL}/api/stream/market`);

    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as {
          type: string;
          channel: string;
          data: Record<string, unknown>;
        };
        const filter = chartFilter.current;

        if (payload.type === 'price') {
          const price = Number(payload.data.price);
          if (payload.data.instrument === filter.instrument) {
            setLivePrice(price);
            updateLastClose(price);
          }
          return;
        }

        if (payload.type === 'candle') {
          const data = payload.data;
          if (
            data.instrument === filter.instrument &&
            data.granularity === filter.granularity
          ) {
            appendCandle({
              time: String(data.time ?? ''),
              instrument: String(data.instrument),
              granularity: String(data.granularity),
              open: Number(data.open ?? 0),
              high: Number(data.high ?? 0),
              low: Number(data.low ?? 0),
              close: Number(data.close ?? 0),
              volume: Number(data.volume ?? 0),
            });
          }
        }
      } catch {
        // ignore malformed SSE payloads
      }
    };

    return () => source.close();
  }, [appendCandle, setLivePrice, updateLastClose]);

  const filteredCandles = useMemo(
    () =>
      candleHistory.filter(
        (c) => c.instrument === instrument && c.granularity === granularity,
      ),
    [candleHistory, instrument, granularity],
  );

  const chartData = useMemo(() => {
    const closes = filteredCandles.map((c) => c.close);
    return filteredCandles.map((c, i) => ({
      time: new Date(c.time).toLocaleString(),
      close: c.close,
      smaFast: smaAt(closes, fastPeriod, i),
      smaSlow: smaAt(closes, slowPeriod, i),
    }));
  }, [filteredCandles, fastPeriod, slowPeriod]);

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-950 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-medium text-slate-300">
          {instrument} · {granularity}
          <span className="ml-2 text-xs text-slate-500">({chartData.length} bars)</span>
        </h3>
        {livePrice != null && (
          <span className="font-mono text-sm text-emerald-400">${livePrice.toFixed(2)}</span>
        )}
      </div>
      {chartData.length === 0 ? (
        <div className="flex h-64 flex-col items-center justify-center text-sm text-slate-500">
          <p>No candle data yet.</p>
          <p className="mt-1 text-xs">Run `make start` and wait ~30s for backfill.</p>
        </div>
      ) : (
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" tick={{ fill: '#94a3b8', fontSize: 10 }} minTickGap={48} />
              <YAxis
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                domain={['auto', 'auto']}
                tickFormatter={(v) => `$${Number(v).toFixed(0)}`}
              />
              <Tooltip
                contentStyle={{ background: '#1e293b', border: '1px solid #475569' }}
                labelStyle={{ color: '#cbd5e1' }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="close"
                name="Close"
                stroke="#38bdf8"
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
              <Line
                type="monotone"
                dataKey="smaFast"
                name={`SMA ${fastPeriod}`}
                stroke="#34d399"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="smaSlow"
                name={`SMA ${slowPeriod}`}
                stroke="#fbbf24"
                strokeWidth={1.5}
                dot={false}
                isAnimationActive={false}
                connectNulls={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
