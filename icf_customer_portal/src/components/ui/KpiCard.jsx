import { SkeletonCard } from './Spinner.jsx';

export default function KpiCard({ label, value, sub, icon: Icon, loading, accent = 'brand' }) {
  if (loading) return <SkeletonCard />;

  const accentColors = {
    brand:   'bg-brand-50   dark:bg-brand-900/20   text-brand-600   dark:text-brand-400',
    emerald: 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400',
    amber:   'bg-amber-50   dark:bg-amber-900/20   text-amber-600   dark:text-amber-400',
    red:     'bg-red-50     dark:bg-red-900/20     text-red-600     dark:text-red-400',
  };

  return (
    <div className="card p-5 flex items-start gap-4">
      {Icon && (
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${accentColors[accent] ?? accentColors.brand}`}>
          <Icon className="w-5 h-5" />
        </div>
      )}
      <div className="min-w-0">
        <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide truncate">{label}</p>
        <p className="text-2xl font-semibold text-gray-900 dark:text-white mt-0.5">{value ?? '—'}</p>
        {sub && <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5 truncate">{sub}</p>}
      </div>
    </div>
  );
}
