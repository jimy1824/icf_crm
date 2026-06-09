import { useState } from 'react';
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell,
  Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend,
} from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { BarChart2, TrendingUp, Users } from 'lucide-react';
import { analyticsApi } from '../../api/analytics.js';
import { useAuth } from '../../hooks/useAuth.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import KpiCard from '../../components/ui/KpiCard.jsx';
import { SkeletonCard } from '../../components/ui/Spinner.jsx';

const COLORS = ['#2563EB', '#10B981', '#F59E0B', '#EF4444', '#7C3AED', '#06B6D4', '#F97316'];
const STAGE_COLORS = { new: '#3B82F6', contacted: '#6366F1', qualified: '#8B5CF6', in_discussion: '#A855F7', proposal_sent: '#F59E0B', closed_won: '#10B981', closed_lost: '#6B7280' };

function ChartCard({ title, subtitle, children, height = 220 }) {
  return (
    <div className="card p-5">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
      {subtitle && <p className="text-xs text-gray-400 mt-0.5 mb-3">{subtitle}</p>}
      <div className="mt-3">{children}</div>
    </div>
  );
}

function FirmView({ firm, firmLoading }) {
  const kpis = [
    { label: 'Total Clients',     value: firm?.total_clients,     icon: Users,      color: 'brand' },
    { label: 'Total Leads',       value: firm?.total_leads,        icon: TrendingUp, color: 'green' },
    { label: 'Active Campaigns',  value: firm?.active_campaigns,   icon: BarChart2,  color: 'violet' },
    { label: 'Firm AUM',          value: firm?.total_aum != null ? `$${(firm.total_aum/1e6).toFixed(1)}M` : null, icon: TrendingUp, color: 'amber' },
  ];

  const growthData = firm?.monthly_growth ?? [];
  const stageData = firm?.pipeline_stages ?? [];
  const advisorData = firm?.advisor_breakdown ?? [];
  const conversionData = firm?.conversion_trend ?? [];

  return (
    <div className="space-y-5">
      {/* KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {firmLoading
          ? [1,2,3,4].map((i) => <SkeletonCard key={i} />)
          : kpis.map((k) => <KpiCard key={k.label} {...k} loading={false} />)}
      </div>

      {/* Charts row 1 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        {/* Client growth trend */}
        <ChartCard title="Client Growth" subtitle="New clients per month (last 12 months)">
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={growthData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="firmGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#2563EB" stopOpacity={0.15} />
                  <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#9CA3AF' }} />
              <YAxis tick={{ fontSize: 10, fill: '#9CA3AF' }} allowDecimals={false} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              <Area type="monotone" dataKey="new_clients" stroke="#2563EB" strokeWidth={2}
                    fill="url(#firmGrad)" dot={{ r: 3, fill: '#2563EB' }} />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>

        {/* Pipeline by stage */}
        <ChartCard title="Pipeline by Stage" subtitle="Current leads across all advisors">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={stageData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="stage" tick={{ fontSize: 9, fill: '#9CA3AF' }} />
              <YAxis tick={{ fontSize: 10, fill: '#9CA3AF' }} allowDecimals={false} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} formatter={(v) => [v, 'Leads']} />
              <Bar dataKey="count" radius={[4,4,0,0]}>
                {stageData.map((d, i) => (
                  <Cell key={i} fill={STAGE_COLORS[d.stage] ?? COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      {/* Charts row 2 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Asset allocation donut */}
        <ChartCard title="Asset Allocation" subtitle="Firm-wide portfolio allocation">
          {(firm?.asset_allocation ?? []).length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={160}>
                <PieChart>
                  <Pie data={firm.asset_allocation} cx="50%" cy="50%" innerRadius={40} outerRadius={65}
                       dataKey="value" nameKey="name" strokeWidth={0}>
                    {firm.asset_allocation.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v) => [`${v}%`, '']} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                </PieChart>
              </ResponsiveContainer>
              <div className="grid grid-cols-2 gap-1 mt-2">
                {firm.asset_allocation.slice(0,6).map((a, i) => (
                  <div key={a.name} className="flex items-center gap-1.5 text-xs">
                    <div className="w-2 h-2 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
                    <span className="text-gray-600 dark:text-gray-400 truncate">{a.name}</span>
                    <span className="font-medium ml-auto">{a.value}%</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="h-40 flex items-center justify-center text-sm text-gray-400">No allocation data</div>
          )}
        </ChartCard>

        {/* Goal progress — horizontal bars */}
        <ChartCard title="Goal Progress" subtitle="On-track vs off-track goals">
          <div className="space-y-3">
            {(firm?.goal_summary ?? []).slice(0,5).map((g) => (
              <div key={g.label}>
                <div className="flex justify-between text-xs text-gray-600 dark:text-gray-400 mb-1">
                  <span className="capitalize">{g.label?.replace(/_/g,' ')}</span>
                  <span className="font-medium">{g.pct ?? 0}%</span>
                </div>
                <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
                  <div className={`h-full rounded-full ${(g.pct ?? 0) >= 70 ? 'bg-success-500' : (g.pct ?? 0) >= 40 ? 'bg-warning-500' : 'bg-danger-500'}`}
                       style={{ width: `${Math.min(g.pct ?? 0, 100)}%` }} />
                </div>
              </div>
            ))}
            {!(firm?.goal_summary ?? []).length && (
              <div className="h-40 flex items-center justify-center text-sm text-gray-400">No goal data</div>
            )}
          </div>
        </ChartCard>

        {/* Advisor breakdown */}
        <ChartCard title="Advisor Performance" subtitle="Clients per advisor">
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={advisorData} layout="vertical" margin={{ top: 4, right: 4, left: 40, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 10, fill: '#9CA3AF' }} />
              <YAxis dataKey="advisor_name" type="category" tick={{ fontSize: 10, fill: '#9CA3AF' }} width={36} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
              <Bar dataKey="client_count" fill="#2563EB" radius={[0,4,4,0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}

function AdvisorView({ advisor, advLoading }) {
  const kpis = [
    { label: 'My Clients', value: advisor?.total_clients, icon: Users, color: 'brand' },
    { label: 'My Leads',   value: advisor?.total_leads,   icon: TrendingUp, color: 'green' },
    { label: 'Conversion', value: advisor?.conversion_rate != null ? `${advisor.conversion_rate}%` : null, icon: BarChart2, color: 'amber' },
    { label: 'Active Campaigns', value: advisor?.active_campaigns, icon: BarChart2, color: 'violet' },
  ];

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {advLoading
          ? [1,2,3,4].map((i) => <SkeletonCard key={i} />)
          : kpis.map((k) => <KpiCard key={k.label} {...k} loading={false} />)}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <ChartCard title="Net Worth Trend" subtitle="Aggregate across my clients (backend — BRU-27)">
          {(advisor?.net_worth_trend ?? []).length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={advisor.net_worth_trend} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <defs>
                  <linearGradient id="advGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10B981" stopOpacity={0.15} />
                    <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="month" tick={{ fontSize: 10, fill: '#9CA3AF' }} />
                <YAxis tick={{ fontSize: 10, fill: '#9CA3AF' }} tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} />
                <Tooltip formatter={(v) => [`$${v.toLocaleString()}`, 'Net Worth']} contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                <Area type="monotone" dataKey="value" stroke="#10B981" strokeWidth={2} fill="url(#advGrad)" dot={{ r: 3, fill: '#10B981' }} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-48 flex items-center justify-center text-sm text-gray-400">No data yet</div>
          )}
        </ChartCard>

        <ChartCard title="My Pipeline by Stage" subtitle="Current leads in my pipeline">
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={advisor?.pipeline_stages ?? []} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="stage" tick={{ fontSize: 9, fill: '#9CA3AF' }} />
              <YAxis tick={{ fontSize: 10, fill: '#9CA3AF' }} allowDecimals={false} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} formatter={(v) => [v, 'Leads']} />
              <Bar dataKey="count" radius={[4,4,0,0]}>
                {(advisor?.pipeline_stages ?? []).map((d, i) => (
                  <Cell key={i} fill={STAGE_COLORS[d.stage] ?? COLORS[i % COLORS.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </div>
  );
}

export default function AnalyticsDashboardPage() {
  const { isFirmAdmin, isTeamLead } = useAuth();
  const [view, setView] = useState(isFirmAdmin() || isTeamLead() ? 'firm' : 'advisor');

  const { data: firm, isLoading: firmLoading } = useQuery({
    queryKey: ['analytics', 'firm'],
    queryFn: analyticsApi.firm,
    enabled: view === 'firm',
  });
  const { data: advisor, isLoading: advLoading } = useQuery({
    queryKey: ['analytics', 'advisor'],
    queryFn: analyticsApi.advisor,
    enabled: view === 'advisor',
  });

  const canSwitchView = isFirmAdmin() || isTeamLead();

  return (
    <div>
      <PageHeader
        title="Analytics"
        subtitle="Firm-wide and advisor-level performance dashboards"
        icon={BarChart2}
        actions={
          canSwitchView && (
            <div className="flex gap-1">
              {['firm', 'advisor'].map((v) => (
                <button key={v} onClick={() => setView(v)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors
                    ${view === v ? 'bg-brand-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'}`}>
                  {v === 'firm' ? 'Firm View' : 'My View'}
                </button>
              ))}
            </div>
          )
        }
      />

      {view === 'firm' && <FirmView firm={firm} firmLoading={firmLoading} />}
      {view === 'advisor' && <AdvisorView advisor={advisor} advLoading={advLoading} />}
    </div>
  );
}
