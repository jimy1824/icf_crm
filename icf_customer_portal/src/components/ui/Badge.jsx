/**
 * Badge — colored pill label.
 *
 * variant: 'blue' | 'green' | 'amber' | 'red' | 'gray' | 'emerald' | 'purple'
 */
const VARIANTS = {
  blue:    'bg-blue-50   text-blue-700   dark:bg-blue-900/30   dark:text-blue-300',
  green:   'bg-green-50  text-green-700  dark:bg-green-900/30  dark:text-green-300',
  emerald: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  amber:   'bg-amber-50  text-amber-700  dark:bg-amber-900/30  dark:text-amber-300',
  red:     'bg-red-50    text-red-700    dark:bg-red-900/30    dark:text-red-300',
  gray:    'bg-gray-100  text-gray-600   dark:bg-gray-700      dark:text-gray-300',
  purple:  'bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
};

export default function Badge({ children, variant = 'gray', className = '' }) {
  return (
    <span className={`badge ${VARIANTS[variant] ?? VARIANTS.gray} ${className}`}>
      {children}
    </span>
  );
}
