import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import { Calendar, ExternalLink, Plus, Video } from 'lucide-react';
import { communicationsApi } from '../../api/communications.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { SkeletonRow } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';

const OUTCOMES = ['completed','no_show','cancelled','rescheduled','pending'];

export default function MeetingsPage() {
  const [showCreate, setShowCreate] = useState(false);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['meetings'],
    queryFn: () => communicationsApi.listMeetings(),
  });

  const { register, handleSubmit, reset } = useForm();

  const createMeeting = useMutation({
    mutationFn: (data) => communicationsApi.createMeeting(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['meetings'] });
      toast.success('Meeting scheduled');
      reset();
      setShowCreate(false);
    },
    onError: (e) => toast.error(e.message),
  });

  const recordOutcome = useMutation({
    mutationFn: ({ id, outcome, notes }) => communicationsApi.meetingOutcome(id, { outcome, notes }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['meetings'] });
      toast.success('Outcome recorded');
    },
    onError: (e) => toast.error(e.message),
  });

  const meetings = data?.results ?? data ?? [];

  return (
    <div>
      <PageHeader
        title="Meetings"
        subtitle="Schedule and track client meetings with Zoom integration"
        icon={Video}
        actions={
          <button onClick={() => setShowCreate(!showCreate)} className="btn-primary btn-sm">
            <Plus className="w-3.5 h-3.5" />
            Schedule Meeting
          </button>
        }
      />

      {showCreate && (
        <div className="card p-5 mb-5">
          <h3 className="section-title mb-4">Schedule Meeting</h3>
          <form onSubmit={handleSubmit((d) => createMeeting.mutate(d))} className="grid grid-cols-2 lg:grid-cols-3 gap-3">
            <div className="space-y-1.5 col-span-2 lg:col-span-1">
              <label className="label">Title</label>
              <input className="input" {...register('title', { required: true })} placeholder="Annual review, intro call…" />
            </div>
            <div className="space-y-1.5">
              <label className="label">Client / Lead ID</label>
              <input className="input" {...register('contact_id', { required: true })} placeholder="ID" />
            </div>
            <div className="space-y-1.5">
              <label className="label">Date & Time</label>
              <input type="datetime-local" className="input" {...register('scheduled_at', { required: true })} />
            </div>
            <div className="space-y-1.5">
              <label className="label">Duration (min)</label>
              <input type="number" className="input" defaultValue={60} {...register('duration_minutes')} />
            </div>
            <div className="space-y-1.5">
              <label className="label">Meeting Type</label>
              <select className="select" {...register('meeting_type')}>
                <option value="zoom">Zoom</option>
                <option value="in_person">In Person</option>
                <option value="phone">Phone</option>
                <option value="teams">Microsoft Teams</option>
              </select>
            </div>
            <div className="space-y-1.5 col-span-full">
              <label className="label">Notes</label>
              <textarea className="textarea" rows={2} {...register('notes')} placeholder="Agenda, preparation notes…" />
            </div>
            <div className="col-span-full flex justify-end gap-2">
              <button type="button" className="btn-outline btn-sm" onClick={() => setShowCreate(false)}>Cancel</button>
              <button type="submit" className="btn-primary btn-sm" disabled={createMeeting.isPending}>
                {createMeeting.isPending && <Spinner size="sm" />}
                Schedule
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead><tr>
            <th className="th">Meeting</th>
            <th className="th">Contact</th>
            <th className="th hidden md:table-cell">Scheduled</th>
            <th className="th hidden md:table-cell">Duration</th>
            <th className="th">Outcome</th>
            <th className="th hidden lg:table-cell">Link</th>
            <th className="th">Record Outcome</th>
          </tr></thead>
          <tbody>
            {isLoading && [1,2,3].map((i) => <SkeletonRow key={i} cols={7} />)}
            {!isLoading && meetings.map((m) => (
              <tr key={m.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/60">
                <td className="td">
                  <p className="text-xs font-medium text-gray-800 dark:text-gray-200">{m.title}</p>
                  <p className="text-[10px] text-gray-400 capitalize">{m.meeting_type}</p>
                </td>
                <td className="td text-xs text-gray-500">{m.contact_name ?? `#${m.contact_id}`}</td>
                <td className="td hidden md:table-cell text-xs text-gray-400">
                  {m.scheduled_at?.slice(0,16).replace('T',' ')}
                </td>
                <td className="td hidden md:table-cell text-xs text-gray-400">
                  {m.duration_minutes ? `${m.duration_minutes}m` : '—'}
                </td>
                <td className="td">
                  {m.outcome ? (
                    <span className="text-xs capitalize text-gray-700 dark:text-gray-300">{m.outcome.replace(/_/g,' ')}</span>
                  ) : (
                    <Badge status="pending" />
                  )}
                </td>
                <td className="td hidden lg:table-cell">
                  {m.zoom_join_url && (
                    <a href={m.zoom_join_url} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700">
                      <ExternalLink className="w-3 h-3" /> Join
                    </a>
                  )}
                </td>
                <td className="td">
                  {!m.outcome && (
                    <select className="select text-xs py-1 h-7"
                      defaultValue=""
                      onChange={(e) => {
                        if (e.target.value) recordOutcome.mutate({ id: m.id, outcome: e.target.value });
                      }}>
                      <option value="">Record…</option>
                      {OUTCOMES.filter((o) => o !== 'pending').map((o) => (
                        <option key={o} value={o}>{o.replace(/_/g,' ')}</option>
                      ))}
                    </select>
                  )}
                </td>
              </tr>
            ))}
            {!isLoading && meetings.length === 0 && (
              <tr><td colSpan={7} className="td py-0">
                <EmptyState icon={Calendar} title="No meetings scheduled"
                  subtitle="Schedule a client meeting to get started." />
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
