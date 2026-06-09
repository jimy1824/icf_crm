const VARIANTS = {
  // Lead/pipeline statuses
  new:          'bg-blue-50  dark:bg-blue-900/30  text-blue-700  dark:text-blue-300',
  contacted:    'bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300',
  qualified:    'bg-violet-50 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300',
  in_discussion:'bg-purple-50 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
  proposal_sent:'bg-amber-50  dark:bg-amber-900/30  text-amber-700  dark:text-amber-300',
  closed_won:   'bg-success-50 dark:bg-success-900/30 text-success-700 dark:text-success-300',
  closed_lost:  'bg-gray-100  dark:bg-gray-800      text-gray-500   dark:text-gray-400',
  // General
  active:   'bg-success-50  dark:bg-success-900/30 text-success-700 dark:text-success-300',
  inactive: 'bg-gray-100    dark:bg-gray-800       text-gray-500   dark:text-gray-400',
  pending:  'bg-amber-50    dark:bg-amber-900/30   text-amber-700  dark:text-amber-300',
  verified: 'bg-success-50  dark:bg-success-900/30 text-success-700 dark:text-success-300',
  rejected: 'bg-danger-50   dark:bg-danger-900/30  text-danger-700 dark:text-danger-300',
  on_hold:  'bg-amber-50    dark:bg-amber-900/30   text-amber-700  dark:text-amber-300',
  // KYC
  kyc_pending:  'bg-amber-50  dark:bg-amber-900/30  text-amber-700 dark:text-amber-300',
  kyc_verified: 'bg-success-50 dark:bg-success-900/30 text-success-700 dark:text-success-300',
  kyc_rejected: 'bg-danger-50  dark:bg-danger-900/30  text-danger-700 dark:text-danger-300',
  // Priority
  urgent:  'bg-red-50    dark:bg-red-900/30   text-red-700   dark:text-red-300',
  high:    'bg-orange-50 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300',
  medium:  'bg-amber-50  dark:bg-amber-900/30  text-amber-700 dark:text-amber-300',
  low:     'bg-gray-100  dark:bg-gray-800      text-gray-500  dark:text-gray-400',
  // Goal
  on_track:  'bg-success-50 dark:bg-success-900/30 text-success-700 dark:text-success-300',
  off_track: 'bg-danger-50  dark:bg-danger-900/30  text-danger-700 dark:text-danger-300',
  achieved:  'bg-brand-50   dark:bg-brand-900/30   text-brand-700  dark:text-brand-300',
  // Campaigns
  draft:   'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-400',
  running: 'bg-success-50 dark:bg-success-900/30 text-success-700 dark:text-success-300',
  paused:  'bg-amber-50 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
  stopped: 'bg-danger-50 dark:bg-danger-900/30 text-danger-700 dark:text-danger-300',
  // Default
  default: 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400',
};

const DOTS = {
  active: 'bg-success-500', running: 'bg-success-500', verified: 'bg-success-500',
  on_track: 'bg-success-500', achieved: 'bg-brand-500',
  pending: 'bg-amber-500', on_hold: 'bg-amber-500', paused: 'bg-amber-500',
  draft: 'bg-gray-400',
  inactive: 'bg-gray-400', closed_lost: 'bg-gray-400', stopped: 'bg-gray-400',
  rejected: 'bg-danger-500', off_track: 'bg-danger-500', closed_won: 'bg-success-500',
  urgent: 'bg-red-500',
};

export default function Badge({ status, showDot = false, className = '', children }) {
  const key = (status ?? '').toLowerCase().replace(/\s+/g, '_');
  const cls = VARIANTS[key] ?? VARIANTS.default;
  const dot = DOTS[key];
  const label = children ?? (status ?? '').replace(/_/g, ' ');
  return (
    <span className={`badge ${cls} ${className}`}>
      {showDot && dot && <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />}
      {label}
    </span>
  );
}
