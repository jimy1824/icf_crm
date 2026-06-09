import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowRight, Clock, Mail, MapPin, MessageSquare, Phone, User, UserPlus,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { leadsApi } from '../../api/leads.js';
import { usersApi } from '../../api/users.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { PageSpinner } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';
import ConfirmModal from '../../components/ui/ConfirmModal.jsx';
import { format } from 'date-fns';

const STAGES = ['new','contacted','qualified','in_discussion','proposal_sent','closed_won','closed_lost'];

function TimelineEntry({ entry }) {
  return (
    <div className="flex gap-3">
      <div className="flex flex-col items-center">
        <div className="w-7 h-7 rounded-full bg-brand-50 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
          <MessageSquare className="w-3 h-3 text-brand-500" />
        </div>
        <div className="w-px flex-1 bg-gray-100 dark:bg-gray-800 mt-1" />
      </div>
      <div className="pb-4 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-xs font-medium text-gray-800 dark:text-gray-200">{entry.actor ?? entry.created_by ?? 'System'}</span>
          <span className="text-[10px] text-gray-400">{entry.created_at?.slice(0, 16).replace('T', ' ')}</span>
          {entry.is_private && <span className="text-[10px] font-medium text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded-full">Private</span>}
        </div>
        <p className="text-sm text-gray-700 dark:text-gray-300">{entry.body ?? entry.note ?? entry.description}</p>
      </div>
    </div>
  );
}

export default function LeadDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [note, setNote] = useState('');
  const [isPrivate, setIsPrivate] = useState(false);
  const [confirm, setConfirm] = useState(null);

  const { data: lead, isLoading, error } = useQuery({
    queryKey: ['lead', id],
    queryFn: () => leadsApi.get(id),
  });
  const { data: timeline } = useQuery({
    queryKey: ['lead-timeline', id],
    queryFn: () => leadsApi.getTimeline(id),
  });
  const { data: advisors } = useQuery({
    queryKey: ['users', 'advisors'],
    queryFn: () => usersApi.list({ role: 'advisor' }),
  });

  const moveStage = useMutation({
    mutationFn: (stage) => leadsApi.moveStage(id, stage),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lead', id] }); toast.success('Stage updated'); },
    onError: (e) => toast.error(e.message),
  });

  const addNote = useMutation({
    mutationFn: () => leadsApi.addNote(id, note, isPrivate),
    onSuccess: () => {
      setNote('');
      qc.invalidateQueries({ queryKey: ['lead-timeline', id] });
      toast.success('Note added');
    },
    onError: (e) => toast.error(e.message),
  });

  const optOut = useMutation({
    mutationFn: () => leadsApi.optOut(id),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['lead', id] }); toast.success('Lead opted out'); setConfirm(null); },
    onError: (e) => toast.error(e.message),
  });

  const convertLead = useMutation({
    mutationFn: () => leadsApi.convert(id, {}),
    onSuccess: (client) => { toast.success('Converted to client!'); navigate(`/clients/${client.id}`); },
    onError: (e) => toast.error(e.message),
  });

  if (isLoading) return <PageSpinner />;
  if (error) return <ErrorAlert error={error} />;
  if (!lead) return null;

  const timelineEntries = timeline?.results ?? timeline ?? [];
  const advisorList = advisors?.results ?? advisors ?? [];

  return (
    <div>
      {confirm && (
        <ConfirmModal {...confirm} onCancel={() => setConfirm(null)} />
      )}

      <PageHeader
        crumbs={[{ label: 'Leads', to: '/leads' }, { label: `${lead.first_name} ${lead.last_name}` }]}
        title={`${lead.first_name} ${lead.last_name}`}
        subtitle={lead.email}
        actions={
          <div className="flex items-center gap-2">
            {lead.status !== 'closed_won' && lead.status !== 'closed_lost' && (
              <button
                className="btn-success btn-sm"
                onClick={() => setConfirm({
                  title: 'Convert to Client',
                  message: `Convert ${lead.first_name} to a full client record?`,
                  onConfirm: () => convertLead.mutate(),
                  loading: convertLead.isPending,
                })}
              >
                <UserPlus className="w-3.5 h-3.5" />
                Convert to Client
              </button>
            )}
            <Link to={`/leads/${id}/edit`} className="btn-outline btn-sm">Edit</Link>
          </div>
        }
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Contact info */}
        <div className="card p-5 space-y-3">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Contact Info</h3>
          {[
            { icon: Mail,  label: 'Email',   value: lead.email },
            { icon: Phone, label: 'Phone',   value: lead.phone },
            { icon: MapPin,label: 'Address', value: [lead.city, lead.state].filter(Boolean).join(', ') },
            { icon: User,  label: 'Advisor', value: lead.assigned_advisor_name ?? `#${lead.assigned_advisor}` },
          ].map(({ icon: Icon, label, value }) => value ? (
            <div key={label} className="flex items-start gap-2.5">
              <Icon className="w-3.5 h-3.5 text-gray-400 mt-0.5 flex-shrink-0" />
              <div>
                <p className="text-[10px] text-gray-400">{label}</p>
                <p className="text-xs text-gray-800 dark:text-gray-200">{value}</p>
              </div>
            </div>
          ) : null)}
          <div className="pt-2 border-t border-gray-100 dark:border-gray-800">
            <Badge status={lead.status} showDot />
            {lead.opt_out && <p className="text-xs text-danger-600 mt-1.5">⛔ Opted out</p>}
          </div>
        </div>

        {/* Stage + pipeline */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Pipeline Stage</h3>
          <div className="space-y-1.5">
            {STAGES.map((s) => (
              <button
                key={s}
                onClick={() => lead.status !== s && moveStage.mutate(s)}
                disabled={moveStage.isPending}
                className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium transition-colors flex items-center justify-between
                  ${lead.status === s
                    ? 'bg-brand-600 text-white'
                    : 'hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-600 dark:text-gray-400'}`}
              >
                <span className="capitalize">{s.replace(/_/g, ' ')}</span>
                {lead.status === s && <ArrowRight className="w-3 h-3" />}
              </button>
            ))}
          </div>
          {!lead.opt_out && (
            <button
              onClick={() => setConfirm({
                title: 'Opt Out Lead',
                message: 'Mark this lead as opted out? No further automated communications will be sent (BRU-07).',
                danger: true,
                onConfirm: () => optOut.mutate(),
                loading: optOut.isPending,
              })}
              className="btn-danger btn-sm w-full justify-center mt-3"
            >
              Mark Opt-Out
            </button>
          )}
        </div>

        {/* Add note */}
        <div className="card p-5">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Add Note</h3>
          <textarea
            className="textarea w-full mb-3"
            rows={4}
            placeholder="Add an activity note…"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
          <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400 mb-3 cursor-pointer">
            <input type="checkbox" checked={isPrivate} onChange={(e) => setIsPrivate(e.target.checked)}
              className="w-3.5 h-3.5 rounded" />
            Private (internal only — BRU-08)
          </label>
          <button
            className="btn-primary btn-sm w-full justify-center"
            disabled={!note.trim() || addNote.isPending}
            onClick={() => addNote.mutate()}
          >
            {addNote.isPending && <Spinner size="sm" />}
            Add Note
          </button>
        </div>
      </div>

      {/* Timeline */}
      <div className="card p-5 mt-5">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
          <Clock className="w-4 h-4 text-gray-400" />
          Activity Timeline
        </h3>
        <div className="space-y-0">
          {timelineEntries.map((e, i) => <TimelineEntry key={e.id ?? i} entry={e} />)}
          {timelineEntries.length === 0 && (
            <p className="text-sm text-gray-400 text-center py-6">No timeline entries yet.</p>
          )}
        </div>
      </div>
    </div>
  );
}
