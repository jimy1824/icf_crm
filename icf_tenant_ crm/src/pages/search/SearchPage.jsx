import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Briefcase, Search, Users, Megaphone, MapPin } from 'lucide-react';
import { searchApi } from '../../api/search.js';
import { useDebounce } from '../../hooks/useDebounce.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Spinner from '../../components/ui/Spinner.jsx';

const TYPE_META = {
  lead:      { icon: Users,     color: 'text-blue-500',   label: 'Lead',      path: '/leads' },
  client:    { icon: Briefcase, color: 'text-green-500',  label: 'Client',    path: '/clients' },
  campaign:  { icon: Megaphone, color: 'text-violet-500', label: 'Campaign',  path: '/campaigns' },
  territory: { icon: MapPin,    color: 'text-amber-500',  label: 'Territory', path: '/territories' },
};

function ResultItem({ result }) {
  const meta = TYPE_META[result.type] ?? { icon: Search, color: 'text-gray-400', label: result.type, path: '' };
  const Icon = meta.icon;
  return (
    <Link to={`${meta.path}/${result.id}`}
      className="flex items-start gap-3 px-5 py-3.5 hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors">
      <div className={`mt-0.5 flex-shrink-0 ${meta.color}`}>
        <Icon className="w-4 h-4" />
      </div>
      <div className="min-w-0">
        <p className="text-sm font-medium text-gray-900 dark:text-white truncate">{result.title ?? result.name}</p>
        {result.subtitle && <p className="text-xs text-gray-500 mt-0.5 truncate">{result.subtitle}</p>}
      </div>
      <span className="ml-auto flex-shrink-0 text-[10px] font-medium text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-full capitalize">
        {meta.label}
      </span>
    </Link>
  );
}

export default function SearchPage() {
  const [q, setQ] = useState('');
  const [type, setType] = useState('');
  const dq = useDebounce(q, 300);

  const { data, isLoading, isFetching } = useQuery({
    queryKey: ['global-search', dq, type],
    queryFn: () => searchApi.global(dq, type ? { type } : {}),
    enabled: dq.length >= 2,
  });

  const results = data?.results ?? data ?? [];
  const grouped = results.reduce((acc, r) => {
    const g = r.type ?? 'other';
    if (!acc[g]) acc[g] = [];
    acc[g].push(r);
    return acc;
  }, {});

  return (
    <div className="max-w-2xl mx-auto">
      <PageHeader title="Global Search" icon={Search} />

      {/* Search box */}
      <div className="relative mb-5">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          autoFocus
          className="input pl-12 pr-4 py-3.5 text-base w-full"
          placeholder="Search leads, clients, campaigns, territories…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        {(isLoading || isFetching) && (
          <Spinner size="sm" className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400" />
        )}
      </div>

      {/* Type filter */}
      <div className="flex gap-1 mb-4 flex-wrap">
        {['', 'lead', 'client', 'campaign', 'territory'].map((t) => (
          <button key={t} onClick={() => setType(t)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors
              ${type === t ? 'bg-brand-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200'}`}>
            {t === '' ? 'All Types' : t}
          </button>
        ))}
      </div>

      {/* Results */}
      {dq.length >= 2 && (
        <div className="card overflow-hidden">
          {results.length === 0 && !isLoading && (
            <div className="px-5 py-12 text-center">
              <Search className="w-8 h-8 text-gray-300 mx-auto mb-3" />
              <p className="text-sm text-gray-500">No results for "<strong>{dq}</strong>"</p>
            </div>
          )}
          {Object.entries(grouped).map(([groupType, items]) => (
            <div key={groupType}>
              <div className="px-5 py-2 bg-gray-50 dark:bg-gray-800/50 border-y border-gray-100 dark:border-gray-700">
                <span className="text-[10px] font-semibold uppercase tracking-wider text-gray-400 capitalize">
                  {TYPE_META[groupType]?.label ?? groupType} ({items.length})
                </span>
              </div>
              <div className="divide-y divide-gray-50 dark:divide-gray-800">
                {items.map((r) => <ResultItem key={`${r.type}-${r.id}`} result={r} />)}
              </div>
            </div>
          ))}
        </div>
      )}
      {dq.length > 0 && dq.length < 2 && (
        <p className="text-xs text-gray-400 text-center py-4">Type at least 2 characters to search…</p>
      )}
      {dq.length === 0 && (
        <div className="text-center py-16">
          <Search className="w-12 h-12 text-gray-200 dark:text-gray-700 mx-auto mb-4" />
          <p className="text-sm text-gray-400">Start typing to search across your firm's data.</p>
          <p className="text-xs text-gray-300 dark:text-gray-600 mt-1">Searches leads, clients, campaigns and territories.</p>
        </div>
      )}
    </div>
  );
}
