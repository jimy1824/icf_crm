import { Link, useSearchParams } from 'react-router-dom';
import { CreditCard } from 'lucide-react';
import { billingApi } from '../../api/tenants.js';
import { useFetch } from '../../hooks/useFetch.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { SkeletonRow } from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';

function centsToDisplay(cents, currency = 'USD') {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency }).format(cents / 100);
}

export default function BillingListPage() {
  const [searchParams] = useSearchParams();
  const tenantId = searchParams.get('tenant_id') || '';

  const { data: records, loading, error } = useFetch(
    () => billingApi.list(tenantId || null),
    [tenantId],
  );

  const rows = records?.results ?? records ?? [];

  return (
    <div>
      <PageHeader
        title={tenantId ? `Billing — Tenant #${tenantId}` : 'Billing Records'}
        subtitle="Invoice history across all tenants."
        crumbs={tenantId ? [
          { label: 'Tenants', to: '/tenants' },
          { label: `Tenant #${tenantId}`, to: `/tenants/${tenantId}` },
          { label: 'Billing' },
        ] : []}
      />

      <ErrorAlert error={error} className="mb-4" />

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50/60 dark:bg-gray-800/60">
            <tr>
              <th className="th">Invoice</th>
              <th className="th hidden md:table-cell">Type</th>
              <th className="th">Amount</th>
              <th className="th hidden lg:table-cell">Period</th>
              <th className="th">Status</th>
              <th className="th hidden md:table-cell">Paid At</th>
              <th className="th w-12" />
            </tr>
          </thead>
          <tbody>
            {loading && [1, 2, 3, 4].map((i) => <SkeletonRow key={i} cols={7} />)}
            {!loading && rows.map((r) => (
              <tr key={r.id} className="hover:bg-gray-50/70 dark:hover:bg-gray-700/30 transition-colors">
                <td className="td">
                  <div className="flex items-center gap-2">
                    <div className="w-7 h-7 rounded-lg bg-gray-50 dark:bg-gray-700 flex items-center justify-center flex-shrink-0">
                      <CreditCard className="w-3.5 h-3.5 text-gray-400" />
                    </div>
                    <span className="font-mono text-xs text-gray-700 dark:text-gray-300">
                      {r.invoice_number || `#${r.id}`}
                    </span>
                  </div>
                </td>
                <td className="td hidden md:table-cell text-gray-500 dark:text-gray-400 capitalize">{r.record_type}</td>
                <td className="td font-medium text-gray-900 dark:text-white">
                  {centsToDisplay(r.amount_cents, r.currency)}
                </td>
                <td className="td hidden lg:table-cell text-xs text-gray-500 dark:text-gray-400 whitespace-nowrap">
                  {r.period_start} – {r.period_end}
                </td>
                <td className="td"><Badge status={r.status} showDot /></td>
                <td className="td hidden md:table-cell text-xs text-gray-400 dark:text-gray-500">
                  {r.paid_at?.slice(0, 10) || '—'}
                </td>
                <td className="td">
                  <Link
                    to={`/billing/${r.id}`}
                    className="text-xs text-brand-600 hover:text-brand-700 font-medium"
                  >
                    View →
                  </Link>
                </td>
              </tr>
            ))}
            {!loading && rows.length === 0 && (
              <tr>
                <td colSpan={7} className="td text-center text-gray-400 py-10">
                  No billing records found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
