import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Users } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { leadsApi } from '../../api/leads.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import DataTable from '../../components/ui/DataTable.jsx';

const ALL_STATUSES = [
  'new', 'contacted', 'qualified', 'in_discussion', 'proposal_sent',
  'closed_won', 'closed_lost', 'client', 'former_client',
];
const SOURCES = ['website', 'referral', 'social', 'email', 'phone', 'other'];

const COLUMNS = [
  {
    key: 'full_name',
    label: 'Name',
    sortable: true,
    render: (row) => (
      <div>
        <Link
          to={`/leads/${row.id}`}
          className="font-medium text-gray-900 dark:text-white hover:text-brand-600 transition-colors"
        >
          {row.full_name ?? `${row.first_name} ${row.last_name}`}
        </Link>
        {row.email && (
          <p className="text-[11px] text-gray-400 mt-0.5 truncate max-w-[200px]">{row.email}</p>
        )}
      </div>
    ),
  },
  {
    key: 'phone',
    label: 'Phone',
    render: (row) => (
      <span className="text-xs text-gray-500">{row.phone || '—'}</span>
    ),
  },
  {
    key: 'status',
    label: 'Status',
    sortable: true,
    render: (row) => <Badge status={row.status} showDot />,
  },
  {
    key: 'territory',
    label: 'Territory',
    sortable: true,
    render: (row) => (
      <span className="text-xs text-gray-500">
        {row.territory?.name || '—'}
      </span>
    ),
  },
  {
    key: 'source',
    label: 'Source',
    render: (row) => (
      <span className="text-xs text-gray-500 capitalize">{row.source || '—'}</span>
    ),
  },
  {
    key: 'assigned_advisor_names',
    label: 'Advisor(s)',
    render: (row) => {
      const names = row.assigned_advisor_names ?? [];
      if (names.length === 0) return <span className="text-xs text-gray-400">—</span>;
      return (
        <div className="text-xs text-gray-500">
          {names.map((n, i) => (
            <span key={i} className="block truncate max-w-[140px]">{n}</span>
          ))}
        </div>
      );
    },
  },
  {
    key: 'created_at',
    label: 'Created',
    sortable: true,
    render: (row) => (
      <span className="text-xs text-gray-400 whitespace-nowrap">
        {row.created_at?.slice(0, 10) || '—'}
      </span>
    ),
  },
  {
    key: '_actions',
    label: '',
    render: (row) => (
      <Link
        to={`/leads/${row.id}`}
        className="text-xs text-brand-600 hover:text-brand-700 font-medium whitespace-nowrap"
      >
        Open →
      </Link>
    ),
  },
];

export default function LeadListPage() {
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [ordering, setOrdering] = useState('-created_at');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [source, setSource] = useState('');

  const params = {
    page,
    page_size: pageSize,
    ordering,
    search,
    status,
    source,
  };

  const { data, isLoading, error } = useQuery({
    queryKey: ['leads', params],
    queryFn: () => leadsApi.list(params),
    keepPreviousData: true,
  });

  const rows = data?.results ?? [];
  const totalCount = data?.count ?? 0;

  function handleSort(field) {
    const bare = field.replace(/^-/, '');
    if (ordering === bare) {
      setOrdering(`-${bare}`);
    } else if (ordering === `-${bare}`) {
      setOrdering(bare);
    } else {
      setOrdering(bare);
    }
    setPage(1);
  }

  function handleSearch(term) {
    setSearch(term);
    setPage(1);
  }

  function handleFilter(key, value) {
    if (key === 'status') setStatus(value);
    if (key === 'source') setSource(value);
    setPage(1);
  }

  const toolbar = (
    <>
      <select
        className="select text-xs py-1.5 h-8 w-44"
        value={status}
        onChange={(e) => handleFilter('status', e.target.value)}
      >
        <option value="">All statuses</option>
        {ALL_STATUSES.map((s) => (
          <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
        ))}
      </select>
      <select
        className="select text-xs py-1.5 h-8 w-36"
        value={source}
        onChange={(e) => handleFilter('source', e.target.value)}
      >
        <option value="">All sources</option>
        {SOURCES.map((s) => (
          <option key={s} value={s} className="capitalize">{s}</option>
        ))}
      </select>
    </>
  );

  return (
    <div>
      <PageHeader
        title="Leads & Clients"
        subtitle={isLoading ? '' : `${totalCount.toLocaleString()} record${totalCount !== 1 ? 's' : ''}`}
        icon={Users}
        actions={
          <Link to="/leads/new" className="btn-primary">
            <Plus className="w-4 h-4" />
            New Lead
          </Link>
        }
      />

      <DataTable
        columns={COLUMNS}
        data={rows}
        loading={isLoading}
        error={error ? 'Failed to load records. Please try again.' : null}
        emptyText="No leads or clients match your filters."
        totalCount={totalCount}
        page={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={(s) => { setPageSize(s); setPage(1); }}
        ordering={ordering}
        onSort={handleSort}
        search={search}
        onSearch={handleSearch}
        searchPlaceholder="Search by name, email, phone…"
        toolbar={toolbar}
        rowKey={(r) => r.id}
        pageSizeOptions={[10, 20, 50]}
      />
    </div>
  );
}
