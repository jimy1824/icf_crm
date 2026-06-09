const VARIANTS = {
  active:              'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800',
  trial:               'bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800',
  suspended:           'bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800',
  grace_period:        'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800',
  read_only:           'bg-gray-100 text-gray-600 border border-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600',
  pending:             'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800',
  paid:                'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800',
  overdue:             'bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800',
  // ticket statuses
  open:                'bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800',
  in_progress:         'bg-violet-50 text-violet-700 border border-violet-200 dark:bg-violet-900/30 dark:text-violet-400 dark:border-violet-800',
  waiting_on_customer: 'bg-purple-50 text-purple-700 border border-purple-200 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-800',
  resolved:            'bg-emerald-50 text-emerald-700 border border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800',
  closed:              'bg-gray-100 text-gray-500 border border-gray-200 dark:bg-gray-700 dark:text-gray-400 dark:border-gray-600',
  // priority
  urgent:   'bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800',
  critical: 'bg-red-50 text-red-700 border border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800',
  high:     'bg-orange-50 text-orange-700 border border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800',
  normal:   'bg-blue-50 text-blue-700 border border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800',
  medium:   'bg-amber-50 text-amber-700 border border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800',
  low:      'bg-gray-100 text-gray-600 border border-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600',
  draft:    'bg-gray-100 text-gray-600 border border-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600',
  default:  'bg-gray-100 text-gray-600 border border-gray-200 dark:bg-gray-700 dark:text-gray-300 dark:border-gray-600',
};

const DOTS = {
  active:              'bg-emerald-500',
  trial:               'bg-blue-500',
  suspended:           'bg-red-500',
  grace_period:        'bg-amber-500',
  pending:             'bg-amber-500',
  paid:                'bg-emerald-500',
  open:                'bg-blue-500',
  in_progress:         'bg-violet-500',
  waiting_on_customer: 'bg-purple-500',
  resolved:            'bg-emerald-500',
  urgent:              'bg-red-500',
  critical:            'bg-red-500',
  high:                'bg-orange-500',
};

const LABELS = {
  waiting_on_customer: 'Waiting',
  in_progress:         'In Progress',
  grace_period:        'Grace Period',
  read_only:           'Read Only',
  feature_request:     'Feature Request',
};

export default function Badge({ status, label, showDot = false, className = '' }) {
  const key = status ?? 'default';
  const cls = VARIANTS[key] ?? VARIANTS.default;
  const dot = DOTS[key];
  const text = label ?? LABELS[key] ?? key.replace(/_/g, ' ');

  return (
    <span className={`badge ${cls} ${className}`}>
      {showDot && dot && <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />}
      {text}
    </span>
  );
}
