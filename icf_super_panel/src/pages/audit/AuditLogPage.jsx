import { useState } from 'react';
import { ChevronLeft, ChevronRight, Filter, Lock, Search } from 'lucide-react';
import { auditApi } from '../../api/audit.js';
import { useFetch } from '../../hooks/useFetch.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import { SkeletonRow } from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';

export default function AuditLogPage() {
  const [filters, setFilters] = useState({ action: '', entity_type: '', page: 1 });

  function set(key, value) {
    setFilters((f) => ({ ...f, [key]: value, page: 1 }));
  }

  const params = { page: filters.page };
  if (filters.action) params.action = filters.action;
  if (filters.entity_type) params.entity_type = filters.entity_type;

  const { data, loading, error } = useFetch(
    () => auditApi.list(params),
    [filters.action, filters.entity_type, filters.page],
  );

  const entries = data?.results ?? data ?? [];
  const totalPages = data?.count ? Math.ceil(data.count / 25) : 1;

  return (
    <div>
      <PageHeader
        title="Audit Log"
        subtitle="Append-only event trail — read only (BRU-33)."
        actions={
          <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-50 dark:bg-amber-900/30 border border-amber-100 dark:border-amber-800">
            <Lock className="w-3 h-3 text-amber-600 dark:text-amber-400" />
            <span className="text-xs font-medium text-amber-700 dark:text-amber-400">Read-only</span>
          </div>
        }
      />

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            className="input pl-10"
            placeholder="Filter by action…"
            value={filters.action}
            onChange={(e) => set('action', e.target.value)}
          />
        </div>
        <div className="relative max-w-xs">
          <Filter className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            className="input pl-10"
            placeholder="Entity type…"
            value={filters.entity_type}
            onChange={(e) => set('entity_type', e.target.value)}
          />
        </div>
      </div>

      <ErrorAlert error={error} className="mb-4" />

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50/60 dark:bg-gray-800/60">
            <tr>
              <th className="th w-40">Timestamp</th>
              <th className="th hidden md:table-cell">Actor</th>
              <th className="th">Action</th>
              <th className="th hidden lg:table-cell">Entity</th>
              <th className="th hidden lg:table-cell">ID</th>
              <th className="th hidden xl:table-cell">Tenant</th>
            </tr>
          </thead>
          <tbody>
            {loading && [1, 2, 3, 4, 5, 6].map((i) => <SkeletonRow key={i} cols={6} />)}
            {!loading && entries.map((e) => (
              <tr key={e.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-700/30 transition-colors">
                <td className="td">
                  <span className="text-[11px] font-mono text-gray-500 dark:text-gray-400 whitespace-nowrap">
                    {e.created_at?.slice(0, 19).replace('T', ' ')}
                  </span>
                </td>
                <td className="td hidden md:table-cell">
                  <span className="text-xs text-gray-700 dark:text-gray-300">{e.actor_email ?? e.actor ?? '(system)'}</span>
                </td>
                <td className="td">
                  <code className="text-[11px] font-mono bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 px-1.5 py-0.5 rounded">
                    {e.action}
                  </code>
                </td>
                <td className="td hidden lg:table-cell text-xs text-gray-500 dark:text-gray-400">{e.entity_type}</td>
                <td className="td hidden lg:table-cell">
                  <span className="text-[11px] font-mono text-gray-400 dark:text-gray-500">{e.entity_id}</span>
                </td>
                <td className="td hidden xl:table-cell text-xs text-gray-400 dark:text-gray-500">{e.tenant ?? '—'}</td>
              </tr>
            ))}
            {!loading && entries.length === 0 && (
              <tr>
                <td colSpan={6} className="td text-center text-gray-400 py-10">
                  No audit entries found.
                </td>
              </tr>
            )}
          </tbody>
        </table>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-gray-100 dark:border-gray-700 bg-gray-50/40 dark:bg-gray-800/40">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Page <span className="font-medium text-gray-800 dark:text-gray-200">{filters.page}</span> of {totalPages}
            </p>
            <div className="flex items-center gap-1">
              <button
                className="w-7 h-7 flex items-center justify-center rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-white dark:hover:bg-gray-700 transition-colors disabled:opacity-40"
                disabled={filters.page <= 1}
                onClick={() => setFilters((f) => ({ ...f, page: f.page - 1 }))}
              >
                <ChevronLeft className="w-3.5 h-3.5 text-gray-600 dark:text-gray-300" />
              </button>
              <button
                className="w-7 h-7 flex items-center justify-center rounded-lg border border-gray-200 dark:border-gray-600 hover:bg-white dark:hover:bg-gray-700 transition-colors disabled:opacity-40"
                disabled={filters.page >= totalPages}
                onClick={() => setFilters((f) => ({ ...f, page: f.page + 1 }))}
              >
                <ChevronRight className="w-3.5 h-3.5 text-gray-600 dark:text-gray-300" />
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
