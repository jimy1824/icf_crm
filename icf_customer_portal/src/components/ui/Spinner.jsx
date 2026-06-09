export default function Spinner({ size = 'md', className = '' }) {
  const sz = size === 'sm' ? 'w-4 h-4 border-2' : size === 'lg' ? 'w-10 h-10 border-4' : 'w-7 h-7 border-[3px]';
  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div className={`${sz} rounded-full border-gray-200 dark:border-gray-700 border-t-brand-600 animate-spin`} />
    </div>
  );
}

export function PageSpinner() {
  return (
    <div className="flex items-center justify-center py-24">
      <Spinner size="lg" />
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="card p-5 space-y-3">
      <div className="skeleton h-4 w-1/3" />
      <div className="skeleton h-8 w-1/2" />
      <div className="skeleton h-3 w-1/4" />
    </div>
  );
}
