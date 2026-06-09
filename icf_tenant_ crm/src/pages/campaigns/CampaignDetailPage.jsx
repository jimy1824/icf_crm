import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Megaphone, Play, Pause, StopCircle, Users } from 'lucide-react';
import { campaignsApi } from '../../api/campaigns.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { PageSpinner, SkeletonRow } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';
import ConfirmModal from '../../components/ui/ConfirmModal.jsx';
import { useState } from 'react';

function StepCard({ step, index }) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className="w-7 h-7 rounded-full bg-brand-100 dark:bg-brand-900/40 flex items-center justify-center flex-shrink-0">
          <span className="text-[10px] font-bold text-brand-600">{index + 1}</span>
        </div>
        <div className="w-px flex-1 bg-gray-100 dark:bg-gray-800 mt-1" />
      </div>
      <div className="pb-4 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-semibold text-gray-800 dark:text-gray-200 capitalize">
            {step.step_type?.replace(/_/g,' ')}
          </span>
          {step.delay_days > 0 && (
            <span className="text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-500 px-2 py-0.5 rounded-full">
              +{step.delay_days}d delay
            </span>
          )}
        </div>
        {step.subject && <p className="text-xs text-gray-600 dark:text-gray-400">Subject: {step.subject}</p>}
        {step.template_name && <p className="text-xs text-gray-500">Template: {step.template_name}</p>}
      </div>
    </div>
  );
}

const STATUS_ACTIONS = {
  draft:   [{ action: 'activate', label: 'Activate',  icon: Play,       cls: 'btn-success btn-sm' }],
  running: [
    { action: 'pause',    label: 'Pause',     icon: Pause,      cls: 'btn-outline btn-sm' },
    { action: 'stop',     label: 'Stop',      icon: StopCircle, cls: 'btn-danger btn-sm' },
  ],
  paused:  [
    { action: 'activate', label: 'Resume',    icon: Play,       cls: 'btn-success btn-sm' },
    { action: 'stop',     label: 'Stop',      icon: StopCircle, cls: 'btn-danger btn-sm' },
  ],
  stopped: [],
};

export default function CampaignDetailPage() {
  const { id } = useParams();
  const qc = useQueryClient();
  const [confirm, setConfirm] = useState(null);

  const { data: campaign, isLoading, error } = useQuery({
    queryKey: ['campaign', id],
    queryFn: () => campaignsApi.get(id),
  });
  const { data: steps } = useQuery({
    queryKey: ['campaign-steps', id],
    queryFn: () => campaignsApi.listSteps(id),
    enabled: !!campaign,
  });
  const { data: enrollments } = useQuery({
    queryKey: ['campaign-enrollments', id],
    queryFn: () => campaignsApi.listEnrollments(id),
    enabled: !!campaign,
  });

  const statusMutation = useMutation({
    mutationFn: ({ action }) => {
      if (action === 'activate') return campaignsApi.activate(id);
      if (action === 'pause')    return campaignsApi.pause(id);
      if (action === 'stop')     return campaignsApi.stop(id);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['campaign', id] });
      qc.invalidateQueries({ queryKey: ['campaigns'] });
      toast.success('Campaign updated');
      setConfirm(null);
    },
    onError: (e) => toast.error(e.message),
  });

  if (isLoading) return <PageSpinner />;
  if (error) return <ErrorAlert error={error} />;
  if (!campaign) return null;

  const stepList = steps?.results ?? steps ?? [];
  const enrollList = enrollments?.results ?? enrollments ?? [];
  const actions = STATUS_ACTIONS[campaign.status] ?? [];

  return (
    <div>
      {confirm && <ConfirmModal {...confirm} onCancel={() => setConfirm(null)} />}

      <PageHeader
        crumbs={[{ label: 'Campaigns', to: '/campaigns' }, { label: campaign.name }]}
        title={campaign.name}
        subtitle={campaign.description}
        icon={Megaphone}
        actions={
          <div className="flex items-center gap-2">
            <Badge status={campaign.status} showDot />
            {actions.map(({ action, label, icon: Icon, cls }) => (
              <button key={action} className={cls}
                onClick={() => setConfirm({
                  title: `${label} Campaign`,
                  message: `${label} "${campaign.name}"?`,
                  danger: action === 'stop',
                  onConfirm: () => statusMutation.mutate({ action }),
                  loading: statusMutation.isPending,
                })}>
                <Icon className="w-3.5 h-3.5" />
                {label}
              </button>
            ))}
            <Link to={`/campaigns/${id}/edit`} className="btn-outline btn-sm">Edit</Link>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Stats */}
        <div className="card p-5">
          <h3 className="section-title mb-4">Performance</h3>
          {[
            { label: 'Enrolled',    value: campaign.enrolled_count ?? 0 },
            { label: 'Opened',      value: campaign.open_rate != null ? `${campaign.open_rate}%` : '—' },
            { label: 'Clicked',     value: campaign.click_rate != null ? `${campaign.click_rate}%` : '—' },
            { label: 'Unsubscribed',value: campaign.unsubscribe_rate != null ? `${campaign.unsubscribe_rate}%` : '—' },
            { label: 'Converted',   value: campaign.conversion_count ?? '—' },
          ].map(({ label, value }) => (
            <div key={label} className="flex justify-between py-2 border-b border-gray-50 dark:border-gray-800 last:border-0">
              <span className="text-xs text-gray-400">{label}</span>
              <span className="text-xs font-semibold text-gray-800 dark:text-gray-200">{value}</span>
            </div>
          ))}
        </div>

        {/* Steps */}
        <div className="card p-5">
          <h3 className="section-title mb-4">Campaign Steps</h3>
          {stepList.length > 0 ? (
            <div>
              {stepList.map((s, i) => <StepCard key={s.id} step={s} index={i} />)}
            </div>
          ) : (
            <p className="text-sm text-gray-400 text-center py-6">No steps defined yet.</p>
          )}
        </div>

        {/* Enrollments */}
        <div className="card overflow-hidden">
          <div className="flex items-center gap-2 px-5 py-4 border-b border-gray-100 dark:border-gray-800">
            <Users className="w-4 h-4 text-gray-400" />
            <h3 className="section-title">Enrolled Leads</h3>
          </div>
          <div className="overflow-y-auto max-h-80">
            {enrollList.slice(0,20).map((e) => (
              <div key={e.id} className="flex items-center justify-between px-4 py-2.5 border-b border-gray-50 dark:border-gray-800 last:border-0">
                <div>
                  <p className="text-xs font-medium text-gray-800 dark:text-gray-200">{e.lead_name ?? `Lead #${e.lead}`}</p>
                  <p className="text-[10px] text-gray-400">{e.enrolled_at?.slice(0,10)}</p>
                </div>
                <Badge status={e.status ?? 'active'} />
              </div>
            ))}
            {enrollList.length === 0 && (
              <p className="text-sm text-gray-400 text-center py-6">No enrollments yet.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
