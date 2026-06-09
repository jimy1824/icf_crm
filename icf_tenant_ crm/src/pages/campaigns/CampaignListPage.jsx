import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Megaphone, Plus, Search } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { campaignsApi } from '../../api/campaigns.js';
import { useDebounce } from '../../hooks/useDebounce.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { SkeletonRow } from '../../components/ui/Spinner.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';

const STATUS_TABS = ['all', 'draft', 'running', 'paused', 'stopped'];

export default function CampaignListPage() {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('all');
  const dq = useDebounce(search, 350);

  const params = {};
  if (dq) params.search = dq;
  if (status !== 'all') params.status = status;

  const { data, isLoading } = useQuery({
    queryKey: ['campaigns', params],
    queryFn: () => campaignsApi.list(params),
  });

  const campaigns = data?.results ?? data ?? [];

  return (
    <div>
      <PageHeader
        title="Campaigns"
        subtitle="Email, SMS and multi-channel lead nurture campaigns"
        icon={Megaphone}
        actions={
          <Link to="/campaigns/new" className="btn-primary">
            <Plus className="w-4 h-4" />
            New Campaign
          </Link>
        }
      />

      {/* Status tabs */}
      <div className="flex gap-1 mb-5 overflow-x-auto">
        {STATUS_TABS.map((t) => (
          <button key={t} onClick={() => setStatus(t)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap capitalize
              ${status === t ? 'bg-brand-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200'}`}>
            {t}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative max-w-sm mb-5">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input className="input pl-10" placeholder="Search campaigns…"
          value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead><tr>
            <th className="th">Campaign</th>
            <th className="th">Status</th>
            <th className="th hidden md:table-cell">Type</th>
            <th className="th hidden lg:table-cell">Enrolled</th>
            <th className="th hidden lg:table-cell">Opens</th>
            <th className="th hidden xl:table-cell">Created</th>
            <th className="th w-10" />
          </tr></thead>
          <tbody>
            {isLoading && [1,2,3,4].map((i) => <SkeletonRow key={i} cols={7} />)}
            {!isLoading && campaigns.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/60 transition-colors">
                <td className="td">
                  <Link to={`/campaigns/${c.id}`}
                    className="font-medium text-gray-900 dark:text-white hover:text-brand-600 transition-colors">
                    {c.name}
                  </Link>
                  {c.description && <p className="text-[10px] text-gray-400 mt-0.5 truncate max-w-[200px]">{c.description}</p>}
                </td>
                <td className="td"><Badge status={c.status} showDot /></td>
                <td className="td hidden md:table-cell text-xs text-gray-500 capitalize">{c.campaign_type?.replace(/_/g,' ')}</td>
                <td className="td hidden lg:table-cell text-xs text-gray-500">{c.enrolled_count ?? 0}</td>
                <td className="td hidden lg:table-cell text-xs text-gray-500">{c.open_rate != null ? `${c.open_rate}%` : '—'}</td>
                <td className="td hidden xl:table-cell text-xs text-gray-400">{c.created_at?.slice(0,10)}</td>
                <td className="td">
                  <Link to={`/campaigns/${c.id}`} className="text-xs text-brand-600 hover:text-brand-700 font-medium">
                    Open →
                  </Link>
                </td>
              </tr>
            ))}
            {!isLoading && campaigns.length === 0 && (
              <tr><td colSpan={7} className="td py-0">
                <EmptyState icon={Megaphone} title="No campaigns found"
                  subtitle="Create your first campaign to start nurturing leads."
                  action={<Link to="/campaigns/new" className="btn-primary btn-sm">New Campaign</Link>} />
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
