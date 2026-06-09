import { ChevronRight } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function PageHeader({ title, subtitle, crumbs = [], actions, icon: Icon }) {
  return (
    <div className="mb-6">
      {crumbs.length > 0 && (
        <nav className="flex items-center gap-1 text-xs text-gray-400 mb-3">
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
        <div className="flex items-center gap-3">
          {Icon && (
            <div className="w-9 h-9 rounded-xl bg-brand-50 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
              <Icon className="w-4.5 h-4.5 text-brand-600 dark:text-brand-400" style={{ width: 18, height: 18 }} />
            </div>
          )}
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">{title}</h1>
            {subtitle && <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>}
          </div>
        </div>
        {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
      </div>
    </div>
  );
}
