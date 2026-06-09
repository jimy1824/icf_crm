import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import { MapPin, UserPlus, X } from 'lucide-react';
import {
  Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer,
  Tooltip, XAxis, YAxis, Area, AreaChart,
} from 'recharts';
import { territoriesApi } from '../../api/territories.js';
import { usersApi } from '../../api/users.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { PageSpinner } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';
import { useAuth } from '../../hooks/useAuth.js';

const COLORS = ['#2563EB', '#10B981', '#F59E0B', '#EF4444', '#7C3AED'];

export default function TerritoryDetailPage() {
  const { id } = useParams();
  const { isFirmAdmin } = useAuth();
  const qc = useQueryClient();
  const [showAssign, setShowAssign] = useState(false);
  const { register, handleSubmit, reset } = useForm();

  const { data: territory, isLoading, error } = useQuery({
    queryKey: ['territory', id],
    queryFn: () => territoriesApi.get(id),
  });
  const { data: advisors } = useQuery({
    queryKey: ['territory-advisors', id],
    queryFn: () => territoriesApi.listAdvisors(id),
  });
  const { data: analytics } = useQuery({
    queryKey: ['territory-analytics', id],
    queryFn: () => territoriesApi.analytics(id),
  });
  const { data: weeklyTrend } = useQuery({
    queryKey: ['territory-trend', id],
    queryFn: () => territoriesApi.weeklyTrend(id),
  });
  const { data: allAdvisors } = useQuery({
    queryKey: ['users', 'advisors'],
    queryFn: () => usersApi.list({ role: 'advisor' }),
  });

  const assign = useMutation({
    mutationFn: (data) => territoriesApi.assignAdvisor(id, data.advisor_id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['territory-advisors', id] });
      toast.success('Advisor assigned');
      reset();
      setShowAssign(false);
    },
    onError: (e) => toast.error(e.message),
  });

  const unassign = useMutation({
    mutationFn: (advisorId) => territoriesApi.unassignAdvisor(id, advisorId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['territory-advisors', id] });
      toast.success('Advisor removed');
    },
    onError: (e) => toast.error(e.message),
  });

  if (isLoading) return <PageSpinner />;
  if (error) return <ErrorAlert error={error} />;
  if (!territory) return null;

  const advisorList = advisors?.results ?? advisors ?? [];
  const allAdvisorList = allAdvisors?.results ?? allAdvisors ?? [];
  const trendData = weeklyTrend?.results ?? weeklyTrend ?? [];
  const leadsByStage = analytics?.leads_by_stage ?? [];

  return (
    <div>
      <PageHeader
        crumbs={[{ label: 'Territories', to: '/territories' }, { label: territory.name }]}
        title={territory.name}
        subtitle={territory.region}
        icon={MapPin}
        actions={
          isFirmAdmin() && (
            <div className="flex items-center gap-2">
              <Badge status={territory.is_active ? 'active' : 'inactive'} showDot />
              <Link to={`/territories/${id}/edit`} className="btn-outline btn-sm">Edit</Link>
            </div>
          )
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Advisors */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="section-title">Assigned Advisors</h3>
            {isFirmAdmin() && (
              <button onClick={() => setShowAssign(!showAssign)} className="btn-ghost btn-xs">
                <UserPlus className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          {showAssign && (
            <form onSubmit={handleSubmit((d) => assign.mutate(d))} className="flex gap-2 mb-3">
              <select className="select flex-1 text-xs" {...register('advisor_id', { required: true })}>
                <option value="">Select advisor…</option>
                {allAdvisorList.map((a) => (
                  <option key={a.id} value={a.id}>{a.first_name} {a.last_name}</option>
                ))}
              </select>
              <button type="submit" className="btn-primary btn-xs" disabled={assign.isPending}>
                {assign.isPending ? <Spinner size="sm" /> : 'Assign'}
              </button>
            </form>
          )}
          <div className="space-y-2">
            {advisorList.map((a) => (
              <div key={a.id} className="flex items-center justify-between py-1.5">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center">
                    <span className="text-xs font-bold text-brand-600">
                      {(a.first_name?.[0] ?? '') + (a.last_name?.[0] ?? '')}
                    </span>
                  </div>
                  <div>
                    <p className="text-xs font-medium text-gray-800 dark:text-gray-200">
                      {a.first_name} {a.last_name}
                    </p>
                    <p className="text-[10px] text-gray-400">{a.email}</p>
                  </div>
                </div>
                {isFirmAdmin() && (
                  <button onClick={() => unassign.mutate(a.id)}
                    className="text-gray-400 hover:text-danger-500 transition-colors">
                    <X className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            ))}
            {advisorList.length === 0 && (
              <p className="text-xs text-gray-400 text-center py-4">No advisors assigned.</p>
            )}
          </div>
        </div>

        {/* Stats + charts */}
        <div className="lg:col-span-2 space-y-5">
          {/* KPI row */}
          <div className="grid grid-cols-4 gap-3">
            {[
              { label: 'Leads',   value: analytics?.total_leads },
              { label: 'Clients', value: analytics?.total_clients },
              { label: 'Campaigns', value: analytics?.active_campaigns },
              { label: 'Conversion', value: analytics?.conversion_rate != null ? `${analytics.conversion_rate}%` : '—' },
            ].map(({ label, value }) => (
              <div key={label} className="card p-3 text-center">
                <p className="text-lg font-bold text-gray-900 dark:text-white">{value ?? '—'}</p>
                <p className="text-[10px] text-gray-400 mt-0.5">{label}</p>
              </div>
            ))}
          </div>

          {/* Leads by stage bar */}
          {leadsByStage.length > 0 && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Leads by Stage</h3>
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={leadsByStage} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="stage" tick={{ fontSize: 9, fill: '#9CA3AF' }} />
                  <YAxis tick={{ fontSize: 10, fill: '#9CA3AF' }} allowDecimals={false} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} formatter={(v) => [v, 'Leads']} />
                  <Bar dataKey="count" radius={[4,4,0,0]}>
                    {leadsByStage.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Weekly trend */}
          {trendData.length > 0 && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Weekly Lead Trend</h3>
              <ResponsiveContainer width="100%" height={140}>
                <AreaChart data={trendData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="tGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#2563EB" stopOpacity={0.1} />
                      <stop offset="95%" stopColor="#2563EB" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="week" tick={{ fontSize: 9, fill: '#9CA3AF' }} />
                  <YAxis tick={{ fontSize: 10, fill: '#9CA3AF' }} allowDecimals={false} />
                  <Tooltip contentStyle={{ fontSize: 12, borderRadius: 8 }} />
                  <Area type="monotone" dataKey="new_leads" stroke="#2563EB" strokeWidth={2}
                        fill="url(#tGrad)" dot={{ r: 3, fill: '#2563EB' }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
