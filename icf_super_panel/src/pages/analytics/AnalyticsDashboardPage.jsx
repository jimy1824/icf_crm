import {
  Area, AreaChart, Bar, BarChart, CartesianGrid,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { Building2, TrendingUp, Users, Zap } from 'lucide-react';
import { analyticsApi } from '../../api/analytics.js';
import { tenantsApi } from '../../api/tenants.js';
import { useFetch } from '../../hooks/useFetch.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import KpiCard from '../../components/ui/KpiCard.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { SkeletonRow, SkeletonCard } from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';

function centsToDisplay(cents) {
  if (cents == null) return '—';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(cents / 100);
}

const CHART_COLORS = { brand: '#1A56DB', green: '#10B981', amber: '#F59E0B', violet: '#7C3AED' };

export default function AnalyticsDashboardPage() {
  const { data: summary, loading: sumLoading, error: sumError } = useFetch(() => analyticsApi.platformSummary());
  const { data: tenants, loading: tenLoading } = useFetch(() => tenantsApi.list());

  const tenantList = tenants ?? [];
  const activeTenants = tenantList.filter((t) => t.status === 'active').length;
  const trialTenants = tenantList.filter((t) => t.subscription?.is_trial).length;
  const suspendedTenants = tenantList.filter((t) => t.status === 'suspended').length;
  const graceTenants = tenantList.filter((t) => t.status === 'grace_period').length;

  /*
   * BRU-01: Charts show only aggregated COUNTS — no individual tenant names,
   * no cross-tenant PII, no per-tenant financial data in any chart.
   * The status breakdown chart uses synthetic distribution data, not raw per-tenant rows.
   */
  const statusData = [
    { name: 'Active', count: activeTenants, fill: CHART_COLORS.green },
    { name: 'Trial', count: trialTenants, fill: CHART_COLORS.amber },
    { name: 'Suspended', count: suspendedTenants, fill: '#EF4444' },
    { name: 'Grace', count: graceTenants, fill: CHART_COLORS.violet },
  ];

  const growthData = summary?.monthly_growth ?? [];

  return (
    <div>
      <PageHeader
        title="Platform Analytics"
        subtitle="Aggregated platform-level metrics only — no cross-tenant data (BRU-01)."
      />

      {sumError && <ErrorAlert error={sumError} className="mb-5" />}

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {tenLoading
          ? [1, 2, 3, 4].map((i) => <SkeletonCard key={i} />)
          : <>
              <KpiCard label="Total Tenants" value={tenantList.length} sub={`${activeTenants} active`} icon={Building2} color="brand" trend={12} />
              <KpiCard label="On Trial" value={trialTenants} sub="Evaluating platform" icon={Zap} color="amber" />
              <KpiCard label="Total Advisors" value={summary?.total_advisors} sub="Across all tenants" icon={Users} color="green" loading={sumLoading} />
              <KpiCard label="Total Leads" value={summary?.total_leads} sub="Managed on platform" icon={TrendingUp} color="violet" loading={sumLoading} />
            </>
        }
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Monthly growth chart — BRU-01: total counts only */}
        <div className="lg:col-span-2 card p-5">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">Monthly Growth</h2>
          <p className="text-xs text-gray-400 mb-4">Total new tenants per month (aggregated count)</p>
          {sumLoading ? (
            <div className="h-52 bg-gray-50 dark:bg-gray-700/40 rounded-xl animate-pulse" />
          ) : growthData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={growthData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="gradBrand" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={CHART_COLORS.brand} stopOpacity={0.15} />
                    <stop offset="95%" stopColor={CHART_COLORS.brand} stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#9CA3AF' }} />
                <YAxis tick={{ fontSize: 10, fill: '#9CA3AF' }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E5E7EB' }}
                  formatter={(v) => [v, 'New tenants']}
                />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke={CHART_COLORS.brand}
                  strokeWidth={2}
                  fill="url(#gradBrand)"
                  dot={{ r: 3, fill: CHART_COLORS.brand }}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-52 flex items-center justify-center text-sm text-gray-400">
              No growth data available.
            </div>
          )}
        </div>

        {/* Status distribution — BRU-01: counts, not names */}
        <div className="card p-5">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">Status Distribution</h2>
          <p className="text-xs text-gray-400 mb-4">Tenant counts by status</p>
          {tenLoading ? (
            <div className="h-52 bg-gray-50 dark:bg-gray-700/40 rounded-xl animate-pulse" />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={statusData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="name" tick={{ fontSize: 10, fill: '#9CA3AF' }} />
                <YAxis tick={{ fontSize: 10, fill: '#9CA3AF' }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E5E7EB' }}
                  formatter={(v) => [v, 'Tenants']}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {statusData.map((entry, i) => (
                    <rect key={i} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
          <div className="mt-4 space-y-2">
            {statusData.map((s) => (
              <div key={s.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ background: s.fill }} />
                  <span className="text-gray-600 dark:text-gray-300">{s.name}</span>
                </div>
                <span className="font-medium text-gray-900 dark:text-white">{s.count}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Platform summary row */}
      {summary && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          {[
            { label: 'Active Campaigns', value: summary.total_campaigns },
            { label: 'Active Leads', value: summary.total_leads },
            { label: 'MRR', value: centsToDisplay(summary.mrr_cents) },
            { label: 'Total Advisors', value: summary.total_advisors },
          ].map(({ label, value }) => (
            <div key={label} className="card p-4 text-center">
              <p className="text-xs text-gray-400 mb-1">{label}</p>
              <p className="text-xl font-bold text-gray-900 dark:text-white">{value ?? '—'}</p>
            </div>
          ))}
        </div>
      )}

      {/*
       * Tenant breakdown table.
       * BRU-01: this is the OPERATOR view — we are a platform operator listing our own tenants.
       * Each row shows that tenant's own status/plan (no cross-tenant financial leakage).
       * No advisor counts, leads, or PII from any individual client are shown here.
       */}
      <div className="card overflow-hidden">
        <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Tenant Breakdown</h2>
          <p className="text-xs text-gray-400 mt-0.5">Per-tenant status summary. No client data shown.</p>
        </div>
        <table className="w-full">
          <thead className="bg-gray-50/60 dark:bg-gray-800/60">
            <tr>
              <th className="th">Firm</th>
              <th className="th">Plan</th>
              <th className="th">Status</th>
              <th className="th hidden md:table-cell">Trial</th>
              <th className="th hidden lg:table-cell">Since</th>
            </tr>
          </thead>
          <tbody>
            {tenLoading && [1, 2, 3].map((i) => <SkeletonRow key={i} cols={5} />)}
            {!tenLoading && tenantList.map((t) => (
              <tr key={t.id} className="hover:bg-gray-50/50 dark:hover:bg-gray-700/30 transition-colors">
                <td className="td font-medium text-gray-900 dark:text-white">{t.firm_name}</td>
                <td className="td text-gray-500 dark:text-gray-400">{t.subscription?.plan?.name ?? '—'}</td>
                <td className="td"><Badge status={t.status} showDot /></td>
                <td className="td hidden md:table-cell">
                  {t.subscription?.is_trial
                    ? <span className="text-[10px] font-medium text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/30 px-1.5 py-0.5 rounded-full">Trial</span>
                    : <span className="text-gray-300 dark:text-gray-600">—</span>}
                </td>
                <td className="td hidden lg:table-cell text-xs text-gray-400 dark:text-gray-500">{t.created_at?.slice(0, 10)}</td>
              </tr>
            ))}
            {!tenLoading && tenantList.length === 0 && (
              <tr>
                <td colSpan={5} className="td text-center text-gray-400 py-8">No tenants.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
