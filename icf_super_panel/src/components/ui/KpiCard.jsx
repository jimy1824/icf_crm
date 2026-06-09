import { TrendingDown, TrendingUp } from 'lucide-react';
import { SkeletonCard } from './Spinner.jsx';

export default function KpiCard({ label, value, sub, trend, icon: Icon, color = 'brand', loading }) {
  if (loading) return <SkeletonCard />;

  const colorMap = {
    brand:  'bg-brand-50 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400',
    green:  'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400',
    amber:  'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400',
    red:    'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400',
    violet: 'bg-violet-50 text-violet-600 dark:bg-violet-900/30 dark:text-violet-400',
  };

  const trendPos = trend > 0;
  const trendNeutral = trend === 0 || trend == null;

  return (
    <div className="card p-5 space-y-4 hover:shadow-card-hover transition-shadow duration-150">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{label}</p>
        {Icon && (
          <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${colorMap[color] ?? colorMap.brand}`}>
            <Icon style={{ width: 18, height: 18 }} />
          </div>
        )}
      </div>

      <div>
        <p className="text-2xl font-bold text-gray-900 dark:text-white leading-none">{value ?? '—'}</p>
        {(sub || trend != null) && (
          <div className="flex items-center gap-1.5 mt-1.5">
            {trend != null && !trendNeutral && (
              <span className={`flex items-center gap-0.5 text-xs font-medium ${trendPos ? 'text-emerald-600' : 'text-red-500'}`}>
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
