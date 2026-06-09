import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { CreditCard } from 'lucide-react';
import { getBillingRecords, getCompanySettings } from '../../api/company.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import DataTable from '../../components/ui/DataTable.jsx';
import Badge from '../../components/ui/Badge.jsx';

const STATUS_BADGE = {
  paid: 'active',
  pending: 'pending',
  failed: 'danger',
  refunded: 'inactive',
};

function cents(n) {
  return `$${(n / 100).toFixed(2)}`;
}

export default function CompanyBillingPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [ordering, setOrdering] = useState('-created_at');
  const [search, setSearch] = useState('');

  const { data: company } = useQuery({
    queryKey: ['company-settings'],
    queryFn: getCompanySettings,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ['company-billing', page, pageSize, ordering, search],
    queryFn: () => getBillingRecords({
      page,
      page_size: pageSize,
      ordering,
      search: search || undefined,
    }),
    keepPreviousData: true,
  });

  const records = data?.results ?? [];
  const total = data?.count ?? 0;
  const sub = company?.subscription;

  const columns = [
    {
      key: 'invoice_number',
      label: 'Invoice #',
      render: (row) => (
        <span className="font-mono text-xs text-gray-900 dark:text-white">
          {row.invoice_number || row.external_invoice_id || `INV-${row.id}`}
        </span>
      ),
    },
    {
      key: 'record_type',
      label: 'Type',
      render: (row) => (
        <span className="capitalize text-xs text-gray-600 dark:text-gray-300">{row.record_type}</span>
      ),
    },
    {
      key: 'amount_cents',
      label: 'Amount',
      sortable: true,
      render: (row) => (
        <div className="text-xs">
          <span className="font-medium text-gray-900 dark:text-white">{cents(row.amount_cents)}</span>
          <span className="text-gray-400 ml-1">{row.currency}</span>
          {row.tax_amount_cents > 0 && (
            <p className="text-[10px] text-gray-400">+ {cents(row.tax_amount_cents)} tax</p>
          )}
        </div>
      ),
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => <Badge status={STATUS_BADGE[row.status] ?? 'inactive'} label={row.status} showDot />,
    },
    {
      key: 'period_start',
      label: 'Period',
      render: (row) => (
        <span className="text-xs text-gray-500">
          {row.period_start} → {row.period_end}
        </span>
      ),
    },
    {
      key: 'created_at',
      label: 'Issued',
      sortable: true,
      render: (row) => (
        <span className="text-xs text-gray-400">
          {row.created_at ? new Date(row.created_at).toLocaleDateString() : '—'}
        </span>
      ),
    },
    {
      key: 'paid_at',
      label: 'Paid',
      render: (row) => (
        <span className="text-xs text-gray-400">
          {row.paid_at ? new Date(row.paid_at).toLocaleDateString() : '—'}
        </span>
      ),
    },
  ];

  return (
    <div>
      <PageHeader
        title="Billing"
        subtitle="Invoices and payment history"
        icon={CreditCard}
      />

      {/* Subscription card */}
      {sub && (
        <div className="card p-5 mt-5 flex items-center justify-between flex-wrap gap-4">
          <div>
            <p className="text-xs text-gray-500 mb-0.5">Current Plan</p>
            <p className="text-lg font-bold text-gray-900 dark:text-white">{sub.plan?.name}</p>
            <p className="text-xs text-gray-400 mt-0.5">
              {sub.is_trial ? `Trial — expires ${sub.trial_expires_at ?? 'N/A'}` : `Billing: ${sub.billing_cycle}`}
            </p>
          </div>
          <div className="flex items-center gap-3 flex-wrap">
            <span className={`inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium
              ${sub.status === 'active' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
              : sub.status === 'trial' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
              : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}
            >
              {sub.status}
            </span>
            {sub.payment_due_date && (
              <span className="text-xs text-yellow-600 dark:text-yellow-400">
                Payment due: {sub.payment_due_date}
              </span>
            )}
          </div>
        </div>
      )}

      <div className="mt-5">
        <DataTable
          columns={columns}
          data={records}
          loading={isLoading}
          error={error ? 'Failed to load billing records.' : null}
          emptyText="No billing records found."
          totalCount={total}
          page={page}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={(s) => { setPageSize(s); setPage(1); }}
          ordering={ordering}
          onSort={(f) => { setOrdering(f); setPage(1); }}
          search={search}
          onSearch={(s) => { setSearch(s); setPage(1); }}
          searchPlaceholder="Search by invoice number…"
          rowKey={(r) => r.id}
        />
      </div>
    </div>
  );
}
