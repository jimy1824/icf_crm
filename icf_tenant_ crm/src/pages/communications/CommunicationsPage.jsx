import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import { Mail, MessageSquare, Phone, Link2 } from 'lucide-react';
import { communicationsApi } from '../../api/communications.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { SkeletonRow } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';

const CHANNEL_ICON = {
  email: Mail,
  sms: MessageSquare,
  call: Phone,
};

const CHANNEL_TABS = ['all', 'email', 'sms', 'call'];

function MailboxConnectCard({ mailboxes, onConnect }) {
  const connected = mailboxes?.find((m) => m.is_active);
  return (
    <div className="card p-5">
      <h3 className="section-title mb-3 flex items-center gap-2">
        <Mail className="w-4 h-4 text-gray-400" /> Email Mailbox
      </h3>
      {connected ? (
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-success-500 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{connected.email}</p>
            <p className="text-xs text-gray-400">{connected.provider} — connected</p>
          </div>
          <Badge status="active" className="ml-auto" />
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-gray-500">Connect a mailbox to send tracked emails.</p>
          <button onClick={onConnect} className="btn-primary btn-sm">
            <Link2 className="w-3.5 h-3.5" />
            Connect Mailbox
          </button>
        </div>
      )}
    </div>
  );
}

export default function CommunicationsPage() {
  const [channel, setChannel] = useState('all');
  const [page, setPage] = useState(1);
  const qc = useQueryClient();

  const params = { page };
  if (channel !== 'all') params.channel = channel;

  const { data, isLoading } = useQuery({
    queryKey: ['comms-timeline', params],
    queryFn: () => communicationsApi.timeline(params),
  });
  const { data: mailboxes } = useQuery({
    queryKey: ['mailboxes'],
    queryFn: () => communicationsApi.listMailboxes(),
  });

  const entries = data?.results ?? data ?? [];
  const count = data?.count ?? entries.length;
  const totalPages = Math.ceil(count / 20);

  return (
    <div>
      <PageHeader
        title="Communications"
        subtitle="Email, SMS and call timeline across all clients"
        icon={MessageSquare}
      />

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5 mb-5">
        <MailboxConnectCard
          mailboxes={mailboxes?.results ?? mailboxes ?? []}
          onConnect={() => toast('OAuth redirect would open here')}
        />
        <div className="card p-5 text-center">
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{count}</p>
          <p className="text-xs text-gray-400 mt-1">Total interactions</p>
        </div>
        <div className="card p-5 text-center">
          <p className="text-2xl font-bold text-brand-600">{entries.filter((e) => e.channel === 'email').length}</p>
          <p className="text-xs text-gray-400 mt-1">Emails</p>
        </div>
        <div className="card p-5 text-center">
          <p className="text-2xl font-bold text-violet-600">{entries.filter((e) => e.channel === 'sms').length}</p>
          <p className="text-xs text-gray-400 mt-1">SMS</p>
        </div>
      </div>

      {/* Channel filter */}
      <div className="flex gap-1 mb-4 overflow-x-auto">
        {CHANNEL_TABS.map((t) => (
          <button key={t} onClick={() => { setChannel(t); setPage(1); }}
            className={`px-4 py-2 rounded-lg text-sm font-medium capitalize transition-colors
              ${channel === t ? 'bg-brand-600 text-white' : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200'}`}>
            {t === 'all' ? 'All Channels' : t.toUpperCase()}
          </button>
        ))}
      </div>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead><tr>
            <th className="th">Channel</th>
            <th className="th">Contact</th>
            <th className="th hidden md:table-cell">Subject / Content</th>
            <th className="th hidden lg:table-cell">Direction</th>
            <th className="th hidden lg:table-cell">Status</th>
            <th className="th hidden xl:table-cell">Date</th>
          </tr></thead>
          <tbody>
            {isLoading && [1,2,3,4,5].map((i) => <SkeletonRow key={i} cols={6} />)}
            {!isLoading && entries.map((e) => {
              const Icon = CHANNEL_ICON[e.channel] ?? MessageSquare;
              return (
                <tr key={e.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/60">
                  <td className="td">
                    <div className="flex items-center gap-2">
                      <Icon className="w-3.5 h-3.5 text-gray-400" />
                      <span className="text-xs capitalize">{e.channel}</span>
                    </div>
                  </td>
                  <td className="td">
                    <p className="text-xs font-medium text-gray-800 dark:text-gray-200">{e.contact_name ?? e.to_address ?? e.phone_number}</p>
                    <p className="text-[10px] text-gray-400">{e.client_name ?? ''}</p>
                  </td>
                  <td className="td hidden md:table-cell">
                    <p className="text-xs text-gray-700 dark:text-gray-300 truncate max-w-[220px]">
                      {e.subject ?? e.body_preview ?? e.content ?? '—'}
                    </p>
                  </td>
                  <td className="td hidden lg:table-cell text-xs text-gray-500 capitalize">{e.direction}</td>
                  <td className="td hidden lg:table-cell"><Badge status={e.status ?? 'sent'} /></td>
                  <td className="td hidden xl:table-cell text-xs text-gray-400">{e.created_at?.slice(0,16).replace('T',' ')}</td>
                </tr>
              );
            })}
            {!isLoading && entries.length === 0 && (
              <tr><td colSpan={6} className="td py-0">
                <EmptyState icon={MessageSquare} title="No communications yet"
                  subtitle="Connect a mailbox or start a campaign to see activity here." />
              </td></tr>
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
