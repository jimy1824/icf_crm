/**
 * DashboardPage — FM-12 Tenant CRM dashboard.
 *
 * My Dashboard / Company Dashboard scope toggle.
 * Sections 2 (Today's Leads) and 3 (Today's Scheduled Activities) use the
 * reusable DataTable component with full server-side pagination, sorting,
 * filtering, and search. No client-side sorting or pagination.
 *
 * BRU-01: scope is enforced server-side; frontend only passes query params.
 */

import { useCallback, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  AlertTriangle, Briefcase, Calendar, Mail,
  MessageSquare, Target, TrendingUp, Users,
} from 'lucide-react';
import {
  Bar, BarChart, CartesianGrid, Cell,
  Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import { useQuery } from '@tanstack/react-query';
import { format } from 'date-fns';

import { analyticsApi } from '../api/analytics.js';
import { notificationsApi } from '../api/notifications.js';
import PageHeader from '../components/ui/PageHeader.jsx';
import KpiCard from '../components/ui/KpiCard.jsx';
import Badge from '../components/ui/Badge.jsx';
import DataTable from '../components/ui/DataTable.jsx';
import { SkeletonCard } from '../components/ui/Spinner.jsx';
import { useAuth } from '../hooks/useAuth.js';

const STAGE_COLORS = {
  new: '#2563EB', contacted: '#7C3AED', qualified: '#0891B2',
  in_discussion: '#F59E0B', proposal_sent: '#EA580C',
  closed_won: '#16A34A', closed_lost: '#EF4444',
};
const BAR_COLORS = [
  '#2563EB', '#10B981', '#F59E0B', '#EF4444',
  '#7C3AED', '#06B6D4', '#EC4899', '#84CC16',
];
const DAYS_OPTIONS = [7, 15, 30];
const FIRM_ADMIN_ROLES = ['tenant_admin', 'firm_admin', 'team_lead'];

// ─── Tiny helpers ─────────────────────────────────────────────────────────────

function ScopeToggle({ scope, onChange }) {
  return (
    <div className="inline-flex rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {['my', 'company'].map((s) => (
        <button
          key={s}
          onClick={() => onChange(s)}
          className={`px-4 py-1.5 text-xs font-medium transition-colors ${
            scope === s
              ? 'bg-brand-600 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
          }`}
        >
          {s === 'my' ? 'My Dashboard' : 'Company Dashboard'}
        </button>
      ))}
    </div>
  );
}

function DaysFilter({ days, onChange }) {
  return (
    <div className="inline-flex rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
      {DAYS_OPTIONS.map((d) => (
        <button
          key={d}
          onClick={() => onChange(d)}
          className={`px-3 py-1 text-xs font-medium transition-colors ${
            days === d
              ? 'bg-brand-600 text-white'
              : 'bg-white dark:bg-gray-800 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
          }`}
        >
          {d}d
        </button>
      ))}
    </div>
  );
}

function SectionHeader({ title, icon: Icon, rightSlot }) {
  return (
    <div className="flex items-center justify-between mb-4">
      <div className="flex items-center gap-2">
        {Icon && <Icon className="w-4 h-4 text-brand-600" />}
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>
      </div>
      {rightSlot}
    </div>
  );
}

function EmptyChart({ text }) {
  return (
    <div className="h-48 flex items-center justify-center text-sm text-gray-400">{text}</div>
  );
}

/** Advisor select dropdown shared by Sections 2 and 3. */
function AdvisorFilter({ advisors, value, onChange, disabled }) {
  return (
    <div className="flex items-center gap-1.5">
      <Users className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className="text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2.5 py-1.5 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500 disabled:opacity-50"
      >
        <option value="">My leads</option>
        <option value="all">All advisors</option>
        {(advisors || []).map((a) => (
          <option key={a.id} value={String(a.id)}>
            {a.full_name} ({a.active_lead_count})
          </option>
        ))}
      </select>
    </div>
  );
}

/** Date picker for the table toolbar. */
function DateFilter({ value, onChange }) {
  return (
    <div className="flex items-center gap-1.5">
      <Calendar className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
      <input
        type="date"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2.5 py-1.5 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-brand-500/30 focus:border-brand-500"
      />
    </div>
  );
}

/** Advisor badge list — never duplicate a row, just list all assignees. */
function AdvisorBadges({ advisors }) {
  if (!advisors?.length) return <span className="text-gray-400">Unassigned</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {advisors.map((a) => (
        <span
          key={a.id}
          className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-brand-50 dark:bg-brand-900/20 text-brand-700 dark:text-brand-300"
        >
          {a.full_name}
        </span>
      ))}
    </div>
  );
}

/** Pipeline stage chip. */
function StageBadge({ stage }) {
  const color = STAGE_COLORS[stage] ?? '#6B7280';
  return (
    <span
      className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium whitespace-nowrap"
      style={{ background: `${color}18`, color }}
    >
      {stage?.replace(/_/g, ' ') ?? '—'}
    </span>
  );
}

/** Activity status chip. */
function StatusBadge({ status }) {
  const palette = {
    executed: 'bg-success-50 text-success-700 dark:bg-success-900/20 dark:text-success-300',
    failed:   'bg-danger-50 text-danger-700 dark:bg-danger-900/20 dark:text-danger-300',
    pending:  'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
    scheduled:'bg-brand-50 text-brand-700 dark:bg-brand-900/20 dark:text-brand-300',
    cancelled:'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500',
    skipped:  'bg-warning-50 text-warning-700 dark:bg-warning-900/20 dark:text-warning-300',
  };
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium whitespace-nowrap ${palette[status] ?? palette.pending}`}>
      {status}
    </span>
  );
}

function ChannelIcon({ type }) {
  if (type === 'sms') return <MessageSquare className="w-3.5 h-3.5 text-brand-500" />;
  return <Mail className="w-3.5 h-3.5 text-green-500" />;
}

// ─── Column definitions ───────────────────────────────────────────────────────

const LEADS_COLUMNS = [
  {
    key: 'first_name',
    label: 'Lead Information',
    sortable: true,
    render: (row) => (
      <div className="min-w-[160px]">
        <Link
          to={`/leads/${row.id}`}
          className="font-semibold text-brand-600 hover:underline block"
        >
          {row.first_name} {row.last_name}
        </Link>
        <span className="text-gray-400 text-[10px] block mt-0.5">{row.email}</span>
        {row.phone && (
          <span className="text-gray-400 text-[10px] block">{row.phone}</span>
        )}
      </div>
    ),
  },
  {
    key: 'territory__name',
    label: 'Territory',
    sortable: true,
    render: (row) => (
      <span className="text-gray-600 dark:text-gray-400 text-xs whitespace-nowrap">
        {row.territory ?? '—'}
      </span>
    ),
  },
  {
    key: 'assigned_advisors',
    label: 'Assigned Advisors',
    sortable: false,
    render: (row) => <AdvisorBadges advisors={row.assigned_advisors} />,
  },
  {
    key: 'campaign',
    label: 'Campaign',
    sortable: false,
    render: (row) =>
      row.campaign ? (
        <span className="truncate max-w-[120px] inline-block text-gray-600 dark:text-gray-300 text-xs">
          {row.campaign}
        </span>
      ) : (
        <span className="text-gray-400 text-xs">—</span>
      ),
  },
  {
    key: 'pipeline_stage',
    label: 'Status',
    sortable: true,
    render: (row) => <StageBadge stage={row.pipeline_stage} />,
  },
  {
    key: 'created_at',
    label: 'Created',
    sortable: true,
    render: (row) => (
      <span className="text-gray-400 text-xs whitespace-nowrap">
        {row.created_at ? format(new Date(row.created_at), 'HH:mm') : '—'}
      </span>
    ),
  },
];

const ACTIVITIES_COLUMNS = [
  {
    key: 'lead__last_name',
    label: 'Lead',
    sortable: true,
    render: (row) => (
      <div className="min-w-[140px]">
        {row.lead_id ? (
          <Link
            to={`/leads/${row.lead_id}`}
            className="font-semibold text-brand-600 hover:underline block"
          >
            {row.lead_name}
          </Link>
        ) : (
          <span className="font-semibold text-gray-700 dark:text-gray-200">{row.lead_name ?? '—'}</span>
        )}
        {row.lead_email && (
          <span className="text-gray-400 text-[10px] block mt-0.5">{row.lead_email}</span>
        )}
        {row.assigned_advisors?.length > 0 && (
          <div className="mt-1"><AdvisorBadges advisors={row.assigned_advisors} /></div>
        )}
      </div>
    ),
  },
  {
    key: 'campaign__name',
    label: 'Campaign',
    sortable: true,
    render: (row) => (
      <span className="truncate max-w-[130px] inline-block text-gray-600 dark:text-gray-300 text-xs">
        {row.campaign_name ?? '—'}
      </span>
    ),
  },
  {
    key: 'step_order',
    label: 'Step',
    sortable: true,
    render: (row) => (
      <span className="font-mono text-xs text-gray-500">#{row.step_order}</span>
    ),
  },
  {
    key: 'step_type',
    label: 'Type',
    sortable: false,
    render: (row) => (
      <span className="inline-flex items-center gap-1 text-xs text-gray-600 dark:text-gray-300">
        <ChannelIcon type={row.step_type} />
        {row.step_type}
      </span>
    ),
  },
  {
    key: 'scheduled_at',
    label: 'Scheduled',
    sortable: true,
    render: (row) => (
      <span className="text-gray-400 text-xs whitespace-nowrap">
        {row.scheduled_at ? format(new Date(row.scheduled_at), 'HH:mm') : '—'}
      </span>
    ),
  },
  {
    key: 'status',
    label: 'Status',
    sortable: true,
    render: (row) => <StatusBadge status={row.status} />,
  },
];

// ─── Main page ────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const { user } = useAuth();
  const today = format(new Date(), 'EEEE, MMMM d');
  const todayISO = format(new Date(), 'yyyy-MM-dd');
  const isFirmAdmin = user?.role && FIRM_ADMIN_ROLES.includes(user.role);

  // ── Global scope toggle ───────────────────────────────────────────────────
  const [scope, setScope] = useState('my');

  // ── Chart filters ─────────────────────────────────────────────────────────
  const [weeklyDays, setWeeklyDays] = useState(7);
  const [territoryDays, setTerritoryDays] = useState(7);

  // ── Section 2: Today's Leads table state ──────────────────────────────────
  const [leadsPage, setLeadsPage] = useState(1);
  const [leadsPageSize, setLeadsPageSize] = useState(20);
  const [leadsOrdering, setLeadsOrdering] = useState('-created_at');
  const [leadsSearch, setLeadsSearch] = useState('');
  const [leadsAdvisorId, setLeadsAdvisorId] = useState('');  // '' = my leads, 'all' = all
  const [leadsDate, setLeadsDate] = useState(todayISO);

  // ── Section 3: Today's Activities table state ─────────────────────────────
  const [activitiesPage, setActivitiesPage] = useState(1);
  const [activitiesPageSize, setActivitiesPageSize] = useState(20);
  const [activitiesOrdering, setActivitiesOrdering] = useState('scheduled_at');
  const [activitiesSearch, setActivitiesSearch] = useState('');
  const [activitiesAdvisorId, setActivitiesAdvisorId] = useState('');
  const [activitiesDate, setActivitiesDate] = useState(todayISO);

  // Reset page when filters change
  const handleLeadsAdvisor = useCallback((v) => { setLeadsAdvisorId(v); setLeadsPage(1); }, []);
  const handleLeadsDate = useCallback((v) => { setLeadsDate(v); setLeadsPage(1); }, []);
  const handleLeadsSearch = useCallback((v) => { setLeadsSearch(v); setLeadsPage(1); }, []);
  const handleLeadsSort = useCallback((f) => { setLeadsOrdering(f); setLeadsPage(1); }, []);

  const handleActAdvisor = useCallback((v) => { setActivitiesAdvisorId(v); setActivitiesPage(1); }, []);
  const handleActDate = useCallback((v) => { setActivitiesDate(v); setActivitiesPage(1); }, []);
  const handleActSearch = useCallback((v) => { setActivitiesSearch(v); setActivitiesPage(1); }, []);
  const handleActSort = useCallback((f) => { setActivitiesOrdering(f); setActivitiesPage(1); }, []);

  // When scope switches to 'my', reset advisor filters back to self
  const handleScopeChange = useCallback((s) => {
    setScope(s);
    if (s === 'my') {
      setLeadsAdvisorId('');
      setActivitiesAdvisorId('');
    }
  }, []);

  // ── Build API params ──────────────────────────────────────────────────────
  const resolveAdvisorParam = (advisorId) => {
    if (scope === 'my') return undefined;        // backend defaults to self
    if (advisorId === 'all') return 'all';
    return advisorId || undefined;
  };

  const leadsParams = useMemo(() => ({
    advisor_id: resolveAdvisorParam(leadsAdvisorId),
    date: leadsDate,
    page: leadsPage,
    page_size: leadsPageSize,
    ordering: leadsOrdering,
    search: leadsSearch || undefined,
  }), [scope, leadsAdvisorId, leadsDate, leadsPage, leadsPageSize, leadsOrdering, leadsSearch]);

  const activitiesParams = useMemo(() => ({
    advisor_id: resolveAdvisorParam(activitiesAdvisorId),
    date: activitiesDate,
    page: activitiesPage,
    page_size: activitiesPageSize,
    ordering: activitiesOrdering,
    search: activitiesSearch || undefined,
  }), [scope, activitiesAdvisorId, activitiesDate, activitiesPage, activitiesPageSize, activitiesOrdering, activitiesSearch]);

  // ── Queries ───────────────────────────────────────────────────────────────

  const advisorQ = useQuery({
    queryKey: ['analytics', 'advisor'],
    queryFn: analyticsApi.advisor,
  });

  const firmQ = useQuery({
    queryKey: ['analytics', 'firm'],
    queryFn: analyticsApi.firm,
    enabled: scope === 'company' && isFirmAdmin,
  });

  const advisorsListQ = useQuery({
    queryKey: ['analytics', 'advisors'],
    queryFn: analyticsApi.advisors,
    staleTime: 5 * 60_000,
  });

  const weeklyQ = useQuery({
    queryKey: ['analytics', 'weekly-leads', scope, weeklyDays],
    queryFn: () => analyticsApi.weeklyLeads(scope, weeklyDays),
  });

  const todayLeadsQ = useQuery({
    queryKey: ['analytics', 'today-leads', leadsParams],
    queryFn: () => analyticsApi.todayLeads(leadsParams),
    keepPreviousData: true,
  });

  const todayActivitiesQ = useQuery({
    queryKey: ['analytics', 'today-activities', activitiesParams],
    queryFn: () => analyticsApi.todayActivities(activitiesParams),
    keepPreviousData: true,
  });

  const todayResponsesQ = useQuery({
    queryKey: ['analytics', 'today-responses', scope],
    queryFn: () => analyticsApi.todayResponses(scope),
  });

  const territoryQ = useQuery({
    queryKey: ['analytics', 'territory-distribution', territoryDays],
    queryFn: () => analyticsApi.territoryDistribution(territoryDays),
  });

  const notifQ = useQuery({
    queryKey: ['notifications', 'unread'],
    queryFn: () => notificationsApi.list({ unread: true }),
  });

  // ── Derived values ────────────────────────────────────────────────────────

  const isCompany = scope === 'company' && isFirmAdmin;
  const kpiSource = isCompany ? firmQ.data : advisorQ.data;
  const kpiLoading = isCompany ? firmQ.isLoading : advisorQ.isLoading;

  const kpiList = isCompany
    ? [
        { label: 'Total Leads',      value: kpiSource?.leads?.total,                    icon: Users,      color: 'brand' },
        { label: 'Converted',         value: kpiSource?.leads?.converted,                icon: Briefcase,  color: 'green' },
        { label: 'Active Campaigns',  value: kpiSource?.campaigns?.active,               icon: Target,     color: 'violet' },
        { label: 'Conversion Rate',   value: kpiSource?.leads?.conversion_rate_pct != null ? `${kpiSource.leads.conversion_rate_pct}%` : null, icon: TrendingUp, color: 'amber' },
      ]
    : [
        { label: 'My Leads',          value: kpiSource?.my_leads,                        icon: Users,      color: 'brand' },
        { label: 'Active Clients',    value: kpiSource?.my_clients,                      icon: Briefcase,  color: 'green' },
        { label: 'Active Campaigns',  value: kpiSource?.active_campaigns,                icon: Target,     color: 'violet' },
        { label: 'Conversion Rate',   value: kpiSource?.conversion_rate != null ? `${kpiSource.conversion_rate}%` : null, icon: TrendingUp, color: 'amber' },
      ];

  const pipelineData = (advisorQ.data?.pipeline_stages ?? []).map((s) => ({
    stage: s.stage?.replace(/_/g, ' '),
    count: s.count,
    fill: STAGE_COLORS[s.stage] ?? '#6B7280',
  }));

  const weeklyData = weeklyQ.data?.data ?? [];

  const todayLeadsData = todayLeadsQ.data?.results ?? [];
  const todayLeadsTotal = todayLeadsQ.data?.count ?? 0;

  const todayActivitiesData = todayActivitiesQ.data?.results ?? [];
  const todayActivitiesTotal = todayActivitiesQ.data?.count ?? 0;

  const todayResponses = todayResponsesQ.data?.results ?? [];

  const territoryData = (territoryQ.data?.results ?? []).map((r, i) => ({
    territory: r.territory,
    leads: r.lead_count,
    fill: BAR_COLORS[i % BAR_COLORS.length],
  }));

  const advisorsList = advisorsListQ.data?.results ?? [];
  const notifs = notifQ.data?.results ?? notifQ.data ?? [];

  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  // ── Section 2 toolbar ─────────────────────────────────────────────────────
  const leadsToolbar = (
    <>
      <AdvisorFilter
        advisors={advisorsList}
        value={leadsAdvisorId}
        onChange={handleLeadsAdvisor}
        disabled={scope === 'my'}
      />
      <DateFilter value={leadsDate} onChange={handleLeadsDate} />
    </>
  );

  // ── Section 3 toolbar ─────────────────────────────────────────────────────
  const activitiesToolbar = (
    <>
      <AdvisorFilter
        advisors={advisorsList}
        value={activitiesAdvisorId}
        onChange={handleActAdvisor}
        disabled={scope === 'my'}
      />
      <DateFilter value={activitiesDate} onChange={handleActDate} />
    </>
  );

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-5">
      {/* ── Header ── */}
      <PageHeader
        title={`${greeting}, ${user?.first_name ?? 'Advisor'}`}
        subtitle={today}
        actions={
          <div className="flex items-center gap-3">
            <ScopeToggle scope={scope} onChange={handleScopeChange} />
            <Link to="/kanban" className="btn-primary text-xs py-1.5 px-3">
              Open Pipeline
            </Link>
          </div>
        }
      />

      {/* ── KPI Row ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {kpiLoading
          ? [1, 2, 3, 4].map((i) => <SkeletonCard key={i} />)
          : kpiList.map((k) => <KpiCard key={k.label} {...k} loading={false} />)}
      </div>

      {/* ── Section 1: Weekly Lead Analytics ── */}
      <div className="card p-5">
        <SectionHeader
          title="Weekly Lead Analytics"
          icon={TrendingUp}
          rightSlot={<DaysFilter days={weeklyDays} onChange={setWeeklyDays} />}
        />
        {weeklyQ.isLoading ? (
          <div className="skeleton h-48 rounded-xl" />
        ) : weeklyData.length > 0 ? (
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={weeklyData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#9CA3AF' }} />
              <YAxis tick={{ fontSize: 10, fill: '#9CA3AF' }} allowDecimals={false} />
              <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E5E7EB' }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="received"  name="Leads Received"  fill="#2563EB" radius={[3, 3, 0, 0]} />
              <Bar dataKey="responded" name="Leads Responded" fill="#10B981" radius={[3, 3, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <EmptyChart text="No lead data for this period." />
        )}
      </div>

      {/* ── Section 2: Today's Leads — Enterprise DataTable ── */}
      <div className="card p-5">
        <SectionHeader
          title={`Today's Leads${todayLeadsTotal > 0 ? ` (${todayLeadsTotal})` : ''}`}
          icon={Users}
          rightSlot={
            <Link to="/leads" className="text-xs text-brand-600 font-medium hover:underline">
              View all leads →
            </Link>
          }
        />
        <DataTable
          columns={LEADS_COLUMNS}
          data={todayLeadsData}
          loading={todayLeadsQ.isLoading || todayLeadsQ.isFetching}
          error={todayLeadsQ.isError ? 'Failed to load leads.' : null}
          emptyText="No leads created on this date."
          totalCount={todayLeadsTotal}
          page={leadsPage}
          pageSize={leadsPageSize}
          pageSizeOptions={[10, 20, 50]}
          onPageChange={setLeadsPage}
          onPageSizeChange={(s) => { setLeadsPageSize(s); setLeadsPage(1); }}
          ordering={leadsOrdering}
          onSort={handleLeadsSort}
          search={leadsSearch}
          onSearch={handleLeadsSearch}
          searchPlaceholder="Search name, email, phone…"
          toolbar={leadsToolbar}
          rowKey={(r) => r.id}
        />
      </div>

      {/* ── Section 3: Today's Scheduled Activities — Enterprise DataTable ── */}
      <div className="card p-5">
        <SectionHeader
          title={`Today's Scheduled Activities${todayActivitiesTotal > 0 ? ` (${todayActivitiesTotal})` : ''}`}
          icon={Calendar}
        />
        <DataTable
          columns={ACTIVITIES_COLUMNS}
          data={todayActivitiesData}
          loading={todayActivitiesQ.isLoading || todayActivitiesQ.isFetching}
          error={todayActivitiesQ.isError ? 'Failed to load activities.' : null}
          emptyText="No activities scheduled for this date."
          totalCount={todayActivitiesTotal}
          page={activitiesPage}
          pageSize={activitiesPageSize}
          pageSizeOptions={[10, 20, 50]}
          onPageChange={setActivitiesPage}
          onPageSizeChange={(s) => { setActivitiesPageSize(s); setActivitiesPage(1); }}
          ordering={activitiesOrdering}
          onSort={handleActSort}
          search={activitiesSearch}
          onSearch={handleActSearch}
          searchPlaceholder="Search lead or campaign…"
          toolbar={activitiesToolbar}
          rowKey={(r) => r.id}
        />
      </div>

      {/* ── Section 4: Today's Responses ── */}
      <div className="card p-5">
        <SectionHeader
          title={`Today's Responses${todayResponsesQ.data?.count > 0 ? ` (${todayResponsesQ.data.count})` : ''}`}
          icon={MessageSquare}
        />
        {todayResponsesQ.isLoading ? (
          <div className="skeleton h-20 rounded-xl" />
        ) : todayResponses.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-gray-100 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
                  {['Lead', 'Advisor', 'Type', 'Preview', 'Time'].map((h) => (
                    <th key={h} className="text-left px-4 py-2.5 text-gray-500 dark:text-gray-400 font-semibold">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
                {todayResponses.map((r) => (
                  <tr key={r.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/40">
                    <td className="px-4 py-3 font-medium text-gray-800 dark:text-gray-200">{r.lead_name}</td>
                    <td className="px-4 py-3 text-gray-500">{r.advisor}</td>
                    <td className="px-4 py-3"><ChannelIcon type={r.response_type} /></td>
                    <td className="px-4 py-3 text-gray-500 max-w-[200px] truncate">{r.message_preview}</td>
                    <td className="px-4 py-3 text-gray-400 whitespace-nowrap">{r.received_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="h-16 flex items-center justify-center text-sm text-gray-400">
            No responses received today.
          </div>
        )}
      </div>

      {/* ── Section 5: Territory Distribution + Pipeline charts ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Territory distribution — horizontal bar */}
        <div className="card p-5 lg:col-span-2">
          <SectionHeader
            title="Territory Lead Distribution"
            icon={Target}
            rightSlot={<DaysFilter days={territoryDays} onChange={setTerritoryDays} />}
          />
          {territoryQ.isLoading ? (
            <div className="skeleton h-48 rounded-xl" />
          ) : territoryData.length > 0 ? (
            <ResponsiveContainer width="100%" height={Math.max(160, territoryData.length * 40)}>
              <BarChart
                data={territoryData}
                layout="vertical"
                margin={{ top: 4, right: 16, left: 4, bottom: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 10, fill: '#9CA3AF' }} allowDecimals={false} />
                <YAxis type="category" dataKey="territory" tick={{ fontSize: 10, fill: '#6B7280' }} width={115} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E5E7EB' }}
                  formatter={(v) => [v, 'Leads']}
                />
                <Bar dataKey="leads" radius={[0, 4, 4, 0]}>
                  {territoryData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChart text="No territory data for this period." />
          )}
        </div>

        {/* Pipeline by stage */}
        <div className="card p-5">
          <SectionHeader title="Pipeline by Stage" icon={TrendingUp} />
          {advisorQ.isLoading ? (
            <div className="skeleton h-48 rounded-xl" />
          ) : pipelineData.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={pipelineData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="stage" tick={{ fontSize: 9, fill: '#9CA3AF' }} angle={-30} textAnchor="end" height={44} />
                <YAxis tick={{ fontSize: 10, fill: '#9CA3AF' }} allowDecimals={false} />
                <Tooltip
                  contentStyle={{ fontSize: 12, borderRadius: 8, border: '1px solid #E5E7EB' }}
                  formatter={(v) => [v, 'Leads']}
                />
                <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                  {pipelineData.map((e, i) => <Cell key={i} fill={e.fill} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <EmptyChart text="No pipeline data." />
          )}
        </div>
      </div>

      {/* ── Bottom: Notifications ── */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-warning-500" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Recent Notifications</h3>
          </div>
          <Link to="/notifications" className="text-xs text-brand-600 font-medium hover:underline">
            View all →
          </Link>
        </div>
        {notifs.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {notifs.slice(0, 6).map((n) => (
              <div
                key={n.id}
                className={`flex items-start gap-3 p-2.5 rounded-lg ${
                  !n.is_read
                    ? 'bg-brand-50 dark:bg-brand-900/20 border border-brand-100 dark:border-brand-800'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-800'
                }`}
              >
                <div className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${!n.is_read ? 'bg-brand-500' : 'bg-gray-300'}`} />
                <div className="min-w-0">
                  <p className="text-xs font-medium text-gray-800 dark:text-gray-200 truncate">
                    {n.title ?? n.event_type?.replace(/\./g, ' ')}
                  </p>
                  <p className="text-[10px] text-gray-400 mt-0.5">{n.created_at?.slice(0, 10)}</p>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-gray-400 text-center py-4">No new notifications</p>
        )}
      </div>
    </div>
  );
}
