import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import { Phone, PhoneIncoming, PhoneOutgoing, ShieldCheck } from 'lucide-react';
import { communicationsApi } from '../../api/communications.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { SkeletonRow } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';

const OUTCOMES = ['connected','voicemail','no_answer','busy','wrong_number','callback_requested'];

export default function CallsPage() {
  const [page, setPage] = useState(1);
  const [showLog, setShowLog] = useState(false);
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['calls', page],
    queryFn: () => communicationsApi.listCalls({ page }),
  });

  const { register, handleSubmit, reset } = useForm();

  const logCall = useMutation({
    mutationFn: (data) => communicationsApi.logCall(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['calls'] });
      toast.success('Call logged');
      reset();
      setShowLog(false);
    },
    onError: (e) => toast.error(e.message),
  });

  const calls = data?.results ?? data ?? [];
  const count = data?.count ?? calls.length;
  const totalPages = Math.ceil(count / 20);

  return (
    <div>
      <PageHeader
        title="Calls"
        subtitle="Click-to-call log and RingCentral integration"
        icon={Phone}
        actions={
          <button onClick={() => setShowLog(!showLog)} className="btn-primary btn-sm">
            <Phone className="w-3.5 h-3.5" />
            Log Call
          </button>
        }
      />

      {/* BRU-32 consent notice */}
      <div className="card p-3 mb-5 border-l-4 border-warning-400 flex items-start gap-3 bg-warning-50 dark:bg-warning-900/20">
        <ShieldCheck className="w-4 h-4 text-warning-500 flex-shrink-0 mt-0.5" />
        <p className="text-xs text-warning-700 dark:text-warning-300">
          <strong>BRU-32:</strong> Verbal consent must be captured before enabling call recording. Consent status is reflected per client.
        </p>
      </div>

      {/* Log call form */}
      {showLog && (
        <div className="card p-5 mb-5">
          <h3 className="section-title mb-4">Log Manual Call</h3>
          <form onSubmit={handleSubmit((d) => logCall.mutate(d))} className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="space-y-1.5">
              <label className="label">Client / Lead ID</label>
              <input className="input" {...register('contact_id', { required: true })} placeholder="ID" />
            </div>
            <div className="space-y-1.5">
              <label className="label">Phone Number</label>
              <input className="input" {...register('phone_number')} placeholder="+1 555 0100" />
            </div>
            <div className="space-y-1.5">
              <label className="label">Outcome</label>
              <select className="select" {...register('outcome')}>
                {OUTCOMES.map((o) => <option key={o} value={o}>{o.replace(/_/g,' ')}</option>)}
              </select>
            </div>
            <div className="space-y-1.5">
              <label className="label">Duration (min)</label>
              <input type="number" className="input" min="0" {...register('duration_minutes')} />
            </div>
            <div className="col-span-full space-y-1.5">
              <label className="label">Notes</label>
              <textarea className="textarea" rows={2} {...register('notes')} placeholder="Call summary…" />
            </div>
            <div className="col-span-full flex justify-end gap-2">
              <button type="button" className="btn-outline btn-sm" onClick={() => setShowLog(false)}>Cancel</button>
              <button type="submit" className="btn-primary btn-sm" disabled={logCall.isPending}>
                {logCall.isPending && <Spinner size="sm" />}
                Log Call
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead><tr>
            <th className="th">Direction</th>
            <th className="th">Contact</th>
            <th className="th hidden md:table-cell">Phone</th>
            <th className="th">Outcome</th>
            <th className="th hidden lg:table-cell">Duration</th>
            <th className="th hidden lg:table-cell">Notes</th>
            <th className="th hidden xl:table-cell">Date</th>
          </tr></thead>
          <tbody>
            {isLoading && [1,2,3].map((i) => <SkeletonRow key={i} cols={7} />)}
            {!isLoading && calls.map((c) => (
              <tr key={c.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/60">
                <td className="td">
                  {c.direction === 'inbound'
                    ? <PhoneIncoming className="w-4 h-4 text-success-500" />
                    : <PhoneOutgoing className="w-4 h-4 text-brand-500" />}
                </td>
                <td className="td">
                  <p className="text-xs font-medium text-gray-800 dark:text-gray-200">{c.contact_name ?? `#${c.contact_id}`}</p>
                </td>
                <td className="td hidden md:table-cell text-xs text-gray-500">{c.phone_number}</td>
                <td className="td">
                  <span className="text-xs capitalize text-gray-700 dark:text-gray-300">{c.outcome?.replace(/_/g,' ')}</span>
                </td>
                <td className="td hidden lg:table-cell text-xs text-gray-400">
                  {c.duration_minutes != null ? `${c.duration_minutes}m` : '—'}
                </td>
                <td className="td hidden lg:table-cell text-xs text-gray-400 truncate max-w-[160px]">{c.notes ?? '—'}</td>
                <td className="td hidden xl:table-cell text-xs text-gray-400">{c.created_at?.slice(0,16).replace('T',' ')}</td>
              </tr>
            ))}
            {!isLoading && calls.length === 0 && (
              <tr><td colSpan={7} className="td text-center text-sm text-gray-400 py-8">No calls logged yet.</td></tr>
            )}
          </tbody>
        </table>
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-2 p-4 border-t border-gray-100 dark:border-gray-800">
            <button className="btn-ghost btn-sm" disabled={page === 1} onClick={() => setPage(page - 1)}>← Prev</button>
            <span className="text-xs text-gray-500">Page {page} of {totalPages}</span>
            <button className="btn-ghost btn-sm" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>Next →</button>
          </div>
        )}
      </div>
    </div>
  );
}
