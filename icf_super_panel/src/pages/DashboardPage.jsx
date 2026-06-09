import { Link } from 'react-router-dom';
import { AlertTriangle, Building2, CreditCard, Ticket, TrendingUp } from 'lucide-react';
import { tenantsApi } from '../api/tenants.js';
import { supportApi } from '../api/support.js';
import { useFetch } from '../hooks/useFetch.js';
import PageHeader from '../components/ui/PageHeader.jsx';
import KpiCard from '../components/ui/KpiCard.jsx';
import Badge from '../components/ui/Badge.jsx';
import { SkeletonRow } from '../components/ui/Spinner.jsx';

export default function DashboardPage() {
  const { data: tenants, loading: tLoading } = useFetch(() => tenantsApi.list());
  const { data: ticketData } = useFetch(() => supportApi.listTickets({ status: 'open' }));
  const { data: billing } = useFetch(() => tenantsApi.billingList ? tenantsApi.billingList() : Promise.resolve([]));

  const tList = tenants ?? [];
  const tickets = ticketData?.results ?? ticketData ?? [];
  const active = tList.filter((t) => t.status === 'active').length;
  const trial = tList.filter((t) => t.subscription?.is_trial).length;
  const suspended = tList.filter((t) => t.status === 'suspended').length;

  return (
    <div>
      <PageHeader
        title="Platform Overview"
        subtitle="Real-time summary of the ICF multi-tenant platform"
      />

      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <KpiCard
          label="Active Tenants"
          value={tLoading ? null : active}
          sub={`${trial} on trial`}
          trend={8}
          icon={Building2}
          color="brand"
          loading={tLoading}
        />
        <KpiCard
          label="Total Tenants"
          value={tLoading ? null : tList.length}
          sub={`${suspended} suspended`}
          trend={12}
          icon={TrendingUp}
          color="green"
          loading={tLoading}
        />
        <KpiCard
          label="Open Tickets"
          value={tickets.length}
          sub="Requiring attention"
          trend={tickets.length > 5 ? -3 : 0}
          icon={Ticket}
          color="amber"
        />
        <KpiCard
          label="Pending Compliance"
          value={trial}
          sub="Trials expiring soon"
          icon={AlertTriangle}
          color="red"
          loading={tLoading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent tenants */}
        <div className="lg:col-span-2 card overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-700">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Recent Tenants</h2>
            <Link to="/tenants" className="text-xs text-brand-600 hover:text-brand-700 font-medium">
              View all →
            </Link>
          </div>
          <table className="w-full">
            <thead className="bg-gray-50/60 dark:bg-gray-800/60">
              <tr>
                <th className="th">Firm</th>
                <th className="th">Plan</th>
                <th className="th">Status</th>
                <th className="th">Since</th>
              </tr>
            </thead>
            <tbody>
              {tLoading && [1, 2, 3, 4].map((i) => <SkeletonRow key={i} cols={4} />)}
              {!tLoading && tList.slice(0, 6).map((t) => (
                <tr key={t.id} className="hover:bg-gray-50/70 dark:hover:bg-gray-700/40 transition-colors">
                  <td className="td">
                    <Link to={`/tenants/${t.id}`} className="font-medium text-gray-900 dark:text-white hover:text-brand-600 dark:hover:text-brand-400 transition-colors">
                      {t.firm_name}
                    </Link>
                    <p className="text-xs text-gray-400 mt-0.5">{t.company_email || '—'}</p>
                  </td>
                  <td className="td text-gray-600 dark:text-gray-300">{t.subscription?.plan?.name ?? '—'}</td>
                  <td className="td"><Badge status={t.status} showDot /></td>
                  <td className="td text-gray-500 dark:text-gray-400">{t.created_at?.slice(0, 10)}</td>
                </tr>
              ))}
              {!tLoading && tList.length === 0 && (
                <tr>
                  <td colSpan={4} className="td text-center text-gray-400 py-8">No tenants yet.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Quick actions + open tickets */}
        <div className="space-y-4">
          <div className="card p-5">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Quick Actions</h2>
            <div className="space-y-2">
              <Link to="/tenants/new" className="btn-primary w-full justify-center text-xs py-2">
                <Building2 className="w-3.5 h-3.5" />
                Provision New Tenant
              </Link>
              <Link to="/plans" className="btn-ghost w-full justify-center text-xs py-2 border border-gray-200 dark:border-gray-600">
                Manage Plans
              </Link>
              <Link to="/billing" className="btn-ghost w-full justify-center text-xs py-2 border border-gray-200 dark:border-gray-600">
                <CreditCard className="w-3.5 h-3.5" />
                View Billing
              </Link>
            </div>
          </div>

          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Open Tickets</h2>
              <Link to="/support" className="text-xs text-brand-600 font-medium">View all →</Link>
            </div>
            <div className="space-y-2.5">
              {tickets.slice(0, 4).map((t) => (
                <Link
                  key={t.id}
                  to={`/support/${t.id}`}
                  className="flex items-start gap-2.5 p-2.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/40 transition-colors group"
                >
                  <Badge status={t.priority ?? 'medium'} className="mt-0.5 flex-shrink-0 text-[10px]" />
                  <div className="min-w-0">
                    <p className="text-xs font-medium text-gray-800 dark:text-gray-200 truncate group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors">
                      {t.subject}
                    </p>
                    <p className="text-[10px] text-gray-400 mt-0.5">#{t.id} · {t.created_at?.slice(0, 10)}</p>
                  </div>
                </Link>
              ))}
              {tickets.length === 0 && (
                <p className="text-xs text-gray-400 text-center py-4">No open tickets</p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
