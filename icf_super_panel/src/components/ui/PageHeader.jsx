import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function PageHeader({ title, subtitle, crumbs = [], actions }) {
  return (
    <div className="mb-6">
      {crumbs.length > 0 && (
        <nav className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500 mb-3" aria-label="Breadcrumb">
          {crumbs.map((c, i) => (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="w-3 h-3" />}
              {c.to
                ? <Link to={c.to} className="hover:text-gray-600 dark:hover:text-gray-300 transition-colors">{c.label}</Link>
                : <span className="text-gray-600 dark:text-gray-300 font-medium">{c.label}</span>}
            </span>
          ))}
        </nav>
      )}

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">{title}</h1>
          {subtitle && <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>}
        </div>
        {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
      </div>
    </div>
  );
}
