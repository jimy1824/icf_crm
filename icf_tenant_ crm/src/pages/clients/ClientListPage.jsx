import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Briefcase, Plus, Search } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { clientsApi } from '../../api/clients.js';
import { useDebounce } from '../../hooks/useDebounce.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { SkeletonRow } from '../../components/ui/Spinner.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';

export default function ClientListPage() {
  const [search, setSearch] = useState('');
  const dq = useDebounce(search, 350);

  const params = {};
  if (dq) params.search = dq;

  const { data, isLoading } = useQuery({
    queryKey: ['clients', params],
    queryFn: () => clientsApi.list(params),
  });

  const clients = data?.results ?? data ?? [];

  return (
    <div>
      <PageHeader
        title="Clients"
        subtitle={`${clients.length} client${clients.length !== 1 ? 's' : ''}`}
        icon={Briefcase}
        actions={
          <Link to="/clients/new" className="btn-primary">
            <Plus className="w-4 h-4" />
            New Client
          </Link>
        }
      />

      <div className="relative max-w-sm mb-5">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input className="input pl-10" placeholder="Search by name, email…"
          value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead>
            <tr>
              <th className="th">Name</th>
              <th className="th hidden md:table-cell">Email</th>
              <th className="th hidden md:table-cell">Phone</th>
              <th className="th">KYC Status</th>
              <th className="th hidden lg:table-cell">Advisor</th>
              <th className="th hidden xl:table-cell">Created</th>
              <th className="th w-10" />
            </tr>
          </thead>
          <tbody>
            {isLoading && [1,2,3,4,5].map((i) => <SkeletonRow key={i} cols={7} />)}
            {!isLoading && clients.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/60 transition-colors">
                <td className="td">
                  <Link to={`/clients/${c.id}`} className="font-medium text-gray-900 dark:text-white hover:text-brand-600 transition-colors">
                    {c.full_name ?? `${c.first_name} ${c.last_name}`}
                  </Link>
                  {c.household_name && <p className="text-[10px] text-gray-400 mt-0.5">{c.household_name}</p>}
                </td>
                <td className="td hidden md:table-cell text-xs text-gray-500">{c.email || '—'}</td>
                <td className="td hidden md:table-cell text-xs text-gray-500">{c.phone || '—'}</td>
                <td className="td"><Badge status={c.kyc_status ?? 'pending'} showDot /></td>
                <td className="td hidden lg:table-cell text-xs text-gray-500">
                  {c.assigned_advisor_name ?? `#${c.assigned_advisor}`}
                </td>
                <td className="td hidden xl:table-cell text-xs text-gray-400">{c.created_at?.slice(0,10)}</td>
                <td className="td">
                  <Link to={`/clients/${c.id}`} className="text-xs text-brand-600 hover:text-brand-700 font-medium">
                    Open →
                  </Link>
                </td>
              </tr>
            ))}
            {!isLoading && clients.length === 0 && (
              <tr><td colSpan={7} className="td py-0">
                <EmptyState icon={Briefcase} title="No clients found"
                  subtitle="Try adjusting your search or add a new client."
                  action={<Link to="/clients/new" className="btn-primary btn-sm">New Client</Link>} />
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
