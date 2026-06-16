import type { NewsItem } from '../store/tradingStore';

interface NewsFeedProps {
  news: NewsItem[];
}

function scoreColor(score: number): string {
  if (score > 0.3) return 'text-emerald-400';
  if (score < -0.3) return 'text-red-400';
  return 'text-slate-400';
}

export function NewsFeed({ news }: NewsFeedProps) {
  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900 p-4">
      <h3 className="mb-3 text-sm font-medium text-slate-300">News Feed</h3>
      {news.length === 0 ? (
        <p className="text-sm text-slate-500">No scored headlines yet.</p>
      ) : (
        <ul className="space-y-2">
          {news.map((item) => (
            <li key={item.id} className="border-b border-slate-800 pb-2 text-sm last:border-0">
              <span className={`font-mono ${scoreColor(item.sentimentScore)}`}>
                [{item.sentimentScore >= 0 ? '+' : ''}
                {item.sentimentScore.toFixed(2)}]
              </span>{' '}
              <span className="text-slate-200">{item.headline}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
