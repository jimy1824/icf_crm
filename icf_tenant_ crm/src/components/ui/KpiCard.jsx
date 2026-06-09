import { TrendingDown, TrendingUp } from 'lucide-react';
import { SkeletonCard } from './Spinner.jsx';

const COLOR_MAP = {
  brand:   { bg: 'bg-brand-50 dark:bg-brand-900/30',   text: 'text-brand-600 dark:text-brand-400' },
  green:   { bg: 'bg-success-50 dark:bg-success-900/30', text: 'text-success-600 dark:text-success-400' },
  amber:   { bg: 'bg-warning-50 dark:bg-warning-900/30', text: 'text-warning-600 dark:text-warning-400' },
  red:     { bg: 'bg-danger-50 dark:bg-danger-900/30',   text: 'text-danger-600 dark:text-danger-400' },
  violet:  { bg: 'bg-violet-50 dark:bg-violet-900/30',  text: 'text-violet-600 dark:text-violet-400' },
  indigo:  { bg: 'bg-indigo-50 dark:bg-indigo-900/30',  text: 'text-indigo-600 dark:text-indigo-400' },
};

export default function KpiCard({ label, value, sub, trend, icon: Icon, color = 'brand', loading, onClick }) {
  if (loading) return <SkeletonCard />;
  const c = COLOR_MAP[color] ?? COLOR_MAP.brand;
  const trendPos = trend > 0;
  const trendNeutral = !trend;
  return (
    <div
      className={`card p-5 space-y-3 transition-shadow duration-150 ${onClick ? 'cursor-pointer hover:shadow-card-hover' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{label}</p>
        {Icon && (
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${c.bg}`}>
            <Icon className={c.text} style={{ width: 18, height: 18 }} />
          </div>
        )}
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900 dark:text-white leading-none">{value ?? '—'}</p>
        {(sub || !trendNeutral) && (
          <div className="flex items-center gap-1.5 mt-1.5">
            {!trendNeutral && (
              <span className={`flex items-center gap-0.5 text-xs font-medium ${trendPos ? 'text-success-600' : 'text-danger-500'}`}>
                {trendPos ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                {Math.abs(trend)}%
              </span>
            )}
            {sub && <p className="text-xs text-gray-400 dark:text-gray-500">{sub}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
