import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { MapPin, Plus, Search } from 'lucide-react';
import { territoriesApi } from '../../api/territories.js';
import { useDebounce } from '../../hooks/useDebounce.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { SkeletonRow } from '../../components/ui/Spinner.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';
import { useAuth } from '../../hooks/useAuth.js';

export default function TerritoryListPage() {
  const { isFirmAdmin } = useAuth();
  const [search, setSearch] = useState('');
  const dq = useDebounce(search, 350);

  const { data, isLoading } = useQuery({
    queryKey: ['territories', dq],
    queryFn: () => territoriesApi.list(dq ? { search: dq } : {}),
  });

  const territories = data?.results ?? data ?? [];

  return (
    <div>
      <PageHeader
        title="Territories"
        subtitle="Geographic and advisory territory management"
        icon={MapPin}
        actions={
          isFirmAdmin() && (
            <Link to="/territories/new" className="btn-primary btn-sm">
              <Plus className="w-3.5 h-3.5" />
              New Territory
            </Link>
          )
        }
      />

      <div className="relative max-w-sm mb-5">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input className="input pl-10" placeholder="Search territories…"
          value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead><tr>
            <th className="th">Territory</th>
            <th className="th hidden md:table-cell">Region</th>
            <th className="th hidden md:table-cell">Advisors</th>
            <th className="th hidden lg:table-cell">Leads</th>
            <th className="th hidden lg:table-cell">Clients</th>
            <th className="th">Status</th>
            <th className="th w-10" />
          </tr></thead>
          <tbody>
            {isLoading && [1,2,3].map((i) => <SkeletonRow key={i} cols={7} />)}
            {!isLoading && territories.map((t) => (
              <tr key={t.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/60">
                <td className="td">
                  <Link to={`/territories/${t.id}`}
                    className="font-medium text-gray-900 dark:text-white hover:text-brand-600 transition-colors">
                    {t.name}
                  </Link>
                  {t.description && <p className="text-[10px] text-gray-400 mt-0.5 truncate max-w-[200px]">{t.description}</p>}
                </td>
                <td className="td hidden md:table-cell text-xs text-gray-500">{t.region ?? '—'}</td>
                <td className="td hidden md:table-cell text-xs text-gray-500">{t.advisor_count ?? 0}</td>
                <td className="td hidden lg:table-cell text-xs text-gray-500">{t.lead_count ?? 0}</td>
                <td className="td hidden lg:table-cell text-xs text-gray-500">{t.client_count ?? 0}</td>
                <td className="td"><Badge status={t.is_active ? 'active' : 'inactive'} showDot /></td>
                <td className="td">
                  <Link to={`/territories/${t.id}`} className="text-xs text-brand-600 hover:text-brand-700 font-medium">
                    Open →
                  </Link>
                </td>
              </tr>
            ))}
            {!isLoading && territories.length === 0 && (
              <tr><td colSpan={7} className="td py-0">
                <EmptyState icon={MapPin} title="No territories found"
                  subtitle="Create territories to organize your firm's coverage areas."
                  action={isFirmAdmin() && <Link to="/territories/new" className="btn-primary btn-sm">New Territory</Link>} />
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
