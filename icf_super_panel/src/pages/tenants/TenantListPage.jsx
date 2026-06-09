import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Building2, Plus, Search } from 'lucide-react';
import { tenantsApi } from '../../api/tenants.js';
import { useFetch } from '../../hooks/useFetch.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { SkeletonRow } from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';
import TenantSlideOut from '../../components/tenants/TenantSlideOut.jsx';

const STATUSES = ['', 'active', 'suspended', 'grace_period', 'read_only'];

export default function TenantListPage() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [slideOutId, setSlideOutId] = useState(null);

  const { data, loading, error } = useFetch(
    () => tenantsApi.list({ search: search || undefined, status: status || undefined }),
    [search, status],
  );

  const tenants = data?.results ?? data ?? [];

  return (
    <div>
      <PageHeader
        title="Tenants"
        subtitle={`${tenants.length} firm${tenants.length !== 1 ? 's' : ''} on the platform`}
        actions={
          <Link to="/tenants/new" className="btn-primary">
            <Plus className="w-4 h-4" />
            Provision Tenant
          </Link>
        }
      />

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            className="input pl-10"
            placeholder="Search firm name or email…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <select className="select w-44" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.filter(Boolean).map((s) => (
            <option key={s} value={s} className="capitalize">{s.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>

      {error && <ErrorAlert error={error} className="mb-4" />}

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50/60 dark:bg-gray-800/60">
            <tr>
              <th className="th">Firm</th>
              <th className="th hidden md:table-cell">Plan</th>
              <th className="th">Status</th>
              <th className="th hidden lg:table-cell">Subdomain</th>
              <th className="th hidden lg:table-cell">Created</th>
              <th className="th w-10" />
            </tr>
          </thead>
          <tbody>
            {loading && [1, 2, 3, 4, 5].map((i) => <SkeletonRow key={i} cols={6} />)}
            {!loading && tenants.map((t) => (
              <tr
                key={t.id}
                className="hover:bg-gray-50/70 dark:hover:bg-gray-700/30 cursor-pointer transition-colors"
                onClick={() => setSlideOutId(t.id)}
              >
                <td className="td">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 rounded-lg bg-brand-50 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
                      <Building2 className="w-4 h-4 text-brand-600 dark:text-brand-400" />
                    </div>
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">{t.firm_name}</p>
                      <p className="text-xs text-gray-400 mt-0.5">{t.company_email || '—'}</p>
                    </div>
                  </div>
                </td>
                <td className="td hidden md:table-cell text-gray-600 dark:text-gray-300">
                  {t.subscription?.plan?.name ?? '—'}
                </td>
                <td className="td">
                  <Badge status={t.status} showDot />
                  {t.subscription?.is_trial && (
                    <span className="ml-2 text-[10px] font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30 px-1.5 py-0.5 rounded-full">
                      Trial
                    </span>
                  )}
                </td>
                <td className="td hidden lg:table-cell text-gray-500 dark:text-gray-400 font-mono text-xs">
                  {t.subdomain || '—'}
                </td>
                <td className="td hidden lg:table-cell text-gray-400 dark:text-gray-500 text-xs">
                  {t.created_at?.slice(0, 10)}
                </td>
                <td className="td" onClick={(e) => e.stopPropagation()}>
                  <Link
                    to={`/tenants/${t.id}`}
                    className="text-xs text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 font-medium whitespace-nowrap"
                  >
                    Open →
                  </Link>
                </td>
              </tr>
            ))}
            {!loading && tenants.length === 0 && (
              <tr>
                <td colSpan={6} className="td text-center text-gray-400 py-12">
                  <Building2 className="w-8 h-8 text-gray-200 dark:text-gray-700 mx-auto mb-2" />
                  No tenants found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {slideOutId && (
        <TenantSlideOut tenantId={slideOutId} onClose={() => setSlideOutId(null)} />
      )}
    </div>
  );
}
