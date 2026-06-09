export default function Spinner({ size = 'md', className = '' }) {
  const s = { sm: 'w-3.5 h-3.5 border-[2px]', md: 'w-5 h-5 border-2', lg: 'w-8 h-8 border-[3px]' }[size];
  return (
    <span className={`inline-block ${s} rounded-full border-current border-t-transparent animate-spin ${className}`} />
  );
}

export function PageSpinner() {
  return (
    <div className="flex items-center justify-center h-48">
      <Spinner size="lg" className="text-brand-500" />
    </div>
  );
}

export function SkeletonRow({ cols = 4 }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} className="td">
          <div className="skeleton h-3.5 rounded w-3/4" />
        </td>
      ))}
    </tr>
  );
}

export function SkeletonCard({ className = '' }) {
  return (
    <div className={`card p-5 space-y-3 ${className}`}>
      <div className="skeleton h-3 w-24" />
      <div className="skeleton h-7 w-16" />
      <div className="skeleton h-2.5 w-32" />
    </div>
  );
}

export function SkeletonText({ lines = 3 }) {
  return (
    <div className="space-y-2">
      {Array.from({ length: lines }).map((_, i) => (
        <div key={i} className={`skeleton h-3 ${i === lines - 1 ? 'w-2/3' : 'w-full'}`} />
      ))}
    </div>
  );
}
