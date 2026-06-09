import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowRight, CheckCircle, Clock, Mail, MessageSquare, Phone, Plus, Send, X,
} from 'lucide-react';
import toast from 'react-hot-toast';
import { getMessages, sendMessage } from '../api/portal.js';
import PageHeader from '../components/ui/PageHeader.jsx';

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

const CHANNEL_META = {
  email: { color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' },
  sms:   { color: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300' },
  call:  { color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' },
};
const CHANNEL_ICON = { email: Mail, sms: MessageSquare, call: Phone };

function fmtTime(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  const now = new Date();
  const diffDays = Math.floor((now - d) / 86400000);
  if (diffDays === 0) return d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7)  return d.toLocaleDateString('en-US', { weekday: 'short' });
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function fmtFull(iso) {
  if (!iso) return '';
  return new Date(iso).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
}

function ChBadge({ channel, size = 'sm' }) {
  const meta = CHANNEL_META[channel] ?? { color: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400' };
  return (
    <span className={`inline-flex items-center font-semibold uppercase tracking-wide rounded
      ${size === 'xs' ? 'text-[9px] px-1 py-px' : 'text-[10px] px-1.5 py-0.5'} ${meta.color}`}>
      {channel}
    </span>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Column 1 — Conversation list item
// ─────────────────────────────────────────────────────────────────────────────

function ConvItem({ msg, selected, onClick }) {
  const isOutbound = msg.direction === 'outbound';
  const preview = (msg.body_preview && msg.body_preview.trim())
    || (msg.body && msg.body.trim())
    || msg.subject
    || (msg.channel === 'call' ? 'Call' : '—');
  const label    = isOutbound ? 'You' : 'Advisor';
  const initials = isOutbound ? 'ME' : 'AD';

  return (
    <button
      onClick={onClick}
      className={`w-full text-left px-3 py-3 border-b border-gray-100 dark:border-gray-800 transition-colors
        flex items-start gap-2.5
        ${selected
          ? 'bg-brand-50 dark:bg-brand-900/20 border-l-2 border-l-brand-500'
          : 'hover:bg-gray-50 dark:hover:bg-gray-800/60 border-l-2 border-l-transparent'
        }`}
    >
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 text-[10px] font-bold mt-0.5
        ${isOutbound
          ? 'bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300'
          : 'bg-gray-200 dark:bg-gray-700 text-gray-600 dark:text-gray-300'
        }`}>
        {initials}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-1 mb-0.5">
          <span className="text-xs font-semibold text-gray-800 dark:text-gray-200">{label}</span>
          <span className="text-[10px] text-gray-400 flex-shrink-0">{fmtTime(msg.sent_at ?? msg.created_at)}</span>
        </div>
        <div className="flex items-center gap-1.5 mb-0.5">
          <ChBadge channel={msg.channel} size="xs" />
          <span className={`text-[10px] ${isOutbound ? 'text-brand-500 dark:text-brand-400' : 'text-gray-400'}`}>
            {isOutbound ? '→ sent' : '← received'}
          </span>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 truncate leading-tight">{preview}</p>
      </div>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Column 2 — Full message view (BRU-08: calls shown as opaque card)
// ─────────────────────────────────────────────────────────────────────────────

function MsgView({ msg }) {
  if (!msg) return (
    <div className="flex flex-col items-center justify-center h-full text-center p-8">
      <MessageSquare className="w-12 h-12 text-gray-200 dark:text-gray-700 mb-3" />
      <p className="text-sm font-medium text-gray-400">No message selected</p>
      <p className="text-xs text-gray-300 dark:text-gray-600 mt-1">Click a conversation on the left</p>
    </div>
  );

  const isOut  = msg.direction === 'outbound';
  const Icon   = CHANNEL_ICON[msg.channel] ?? MessageSquare;
  const isCall = msg.channel === 'call';

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900">

      {/* Header */}
      <div className="flex-shrink-0 px-6 py-4 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-start gap-3">
          <div className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0
            ${isOut ? 'bg-brand-100 dark:bg-brand-900/40' : 'bg-gray-100 dark:bg-gray-800'}`}>
            <Icon className={`w-4 h-4 ${isOut ? 'text-brand-600 dark:text-brand-400' : 'text-gray-500 dark:text-gray-400'}`} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm font-semibold text-gray-800 dark:text-gray-100">
                {isOut ? 'You' : 'Your Advisor'}
              </span>
              <ChBadge channel={msg.channel} />
              <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full
                ${isOut
                  ? 'bg-brand-50 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400'
                  : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400'
                }`}>
                {isOut ? 'Sent' : 'Received'}
              </span>
            </div>
            <p className="text-xs text-gray-400 mt-0.5">{fmtFull(msg.sent_at ?? msg.created_at)}</p>
          </div>
        </div>

        {msg.subject && (
          <p className="mt-3 text-base font-semibold text-gray-800 dark:text-gray-100 leading-snug">
            {msg.subject}
          </p>
        )}
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-6 py-5">
        {isCall ? (
          /* BRU-08: no duration/outcome/notes exposed to customer */
          <div className="rounded-2xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 px-5 py-4 space-y-2">
            <div className="flex items-center gap-2">
              <Phone className="w-5 h-5 text-amber-600 dark:text-amber-400" />
              <span className="text-sm font-semibold text-amber-800 dark:text-amber-300">Call from your advisor</span>
            </div>
            <p className="text-sm text-amber-600 dark:text-amber-500">{fmtFull(msg.sent_at ?? msg.created_at)}</p>
          </div>
        ) : (
          <div className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-wrap">
            {(msg.body && msg.body.trim()) || (msg.body_preview && msg.body_preview.trim())
              ? (msg.body && msg.body.trim() ? msg.body : msg.body_preview)
              : <span className="italic text-gray-400">No message body</span>
            }
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="flex-shrink-0 border-t border-gray-100 dark:border-gray-800 px-6 py-3">
        <div className="flex items-center gap-4 text-[10px] text-gray-400 flex-wrap">
          {msg.created_at && <span>Date: {fmtFull(msg.created_at)}</span>}
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Compose modal
// ─────────────────────────────────────────────────────────────────────────────

function ComposeModal({ onClose, onSent }) {
  const [step, setStep]       = useState('pick');
  const [channel, setChannel] = useState('email');
  const [subject, setSubject] = useState('');
  const [body, setBody]       = useState('');

  const send = useMutation({
    mutationFn: sendMessage,
    onSuccess: (sent) => {
      toast.success('Message sent to your advisor');
      onSent(sent);
      onClose();
    },
    onError: (e) => toast.error(e.message || 'Failed to send'),
  });

  function handleSend() {
    if (!body.trim()) { toast.error('Message body is required'); return; }
    const payload = { body: body.trim(), channel };
    if (subject.trim()) payload.subject = subject.trim();
    send.mutate(payload);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-800">
          <div className="flex items-center gap-2">
            {step === 'compose' && (
              <button onClick={() => setStep('pick')} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 mr-1 transition-colors">
                <ArrowRight className="w-4 h-4 rotate-180" />
              </button>
            )}
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              {step === 'pick' ? 'New Message' : `New ${channel === 'email' ? 'Email' : 'SMS'}`}
            </h3>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step 1: pick channel */}
        {step === 'pick' && (
          <div className="p-5 space-y-3">
            <p className="text-xs text-gray-500 dark:text-gray-400">How would you like to reach out?</p>
            <div className="grid grid-cols-2 gap-3">
              {[
                { ch: 'email', Icon: Mail,          title: 'Email',  desc: 'Send a detailed email message' },
                { ch: 'sms',   Icon: MessageSquare, title: 'SMS',    desc: 'Send a short text message' },
              ].map(({ ch, Icon: Ic, title, desc }) => (
                <button
                  key={ch}
                  onClick={() => { setChannel(ch); setStep('compose'); }}
                  className="flex flex-col items-start gap-2 p-4 rounded-xl border-2 border-gray-100 dark:border-gray-800
                    hover:border-brand-400 hover:bg-brand-50 dark:hover:bg-brand-900/20
                    dark:hover:border-brand-600 transition-all text-left group"
                >
                  <div className="w-9 h-9 rounded-lg bg-gray-100 dark:bg-gray-800 group-hover:bg-brand-100 dark:group-hover:bg-brand-900/40
                    flex items-center justify-center transition-colors">
                    <Ic className="w-4 h-4 text-gray-500 dark:text-gray-400 group-hover:text-brand-600 dark:group-hover:text-brand-400 transition-colors" />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-gray-800 dark:text-gray-100 group-hover:text-brand-700 dark:group-hover:text-brand-300 transition-colors">{title}</p>
                    <p className="text-xs text-gray-400 mt-0.5">{desc}</p>
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Step 2: compose */}
        {step === 'compose' && (
          <div className="p-5 space-y-3">
            {channel === 'email' && (
              <input
                type="text"
                value={subject}
                onChange={(e) => setSubject(e.target.value)}
                placeholder="Subject (optional)"
                className="input text-sm h-9 w-full"
              />
            )}
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) handleSend(); }}
              placeholder={`Write your ${channel === 'email' ? 'email' : 'SMS'} to your advisor…  ⌘↵ to send`}
              rows={5}
              className="input resize-none text-sm w-full"
            />
            <div className="flex items-center justify-between">
              <span className="text-[10px] text-gray-400">{body.length} chars</span>
              <button
                onClick={handleSend}
                disabled={send.isPending || !body.trim()}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-brand-600 hover:bg-brand-700 disabled:opacity-50 text-white text-sm font-semibold transition-colors shadow-sm"
              >
                {send.isPending
                  ? <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  : <Send className="w-4 h-4" />
                }
                Send
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────────

export default function MessagesPage() {
  const queryClient = useQueryClient();
  const [channelFilter, setChannelFilter] = useState('');
  const [search, setSearch]               = useState('');
  const [page, setPage]                   = useState(1);
  const [selected, setSelected]           = useState(null);
  const [composeOpen, setComposeOpen]     = useState(false);

  const params = { page, page_size: 30 };
  if (channelFilter) params.channel = channelFilter;

  const { data, isLoading } = useQuery({
    queryKey: ['portal-messages', page, channelFilter],
    queryFn: () => getMessages(params),
    keepPreviousData: true,
  });

  const allMessages = data?.results ?? data ?? [];
  const totalCount  = data?.count ?? allMessages.length;
  const totalPages  = Math.max(1, Math.ceil(totalCount / 30));

  const messages = search.trim()
    ? allMessages.filter(m => {
        const q = search.toLowerCase();
        return (m.subject ?? '').toLowerCase().includes(q)
          || (m.body_preview ?? '').toLowerCase().includes(q)
          || (m.body ?? '').toLowerCase().includes(q);
      })
    : allMessages;

  // Auto-select latest message when data first loads
  useEffect(() => {
    if (!selected && allMessages.length > 0) {
      setSelected(allMessages[0]);
    }
  }, [allMessages.length]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleSent(sent) {
    queryClient.invalidateQueries({ queryKey: ['portal-messages'] });
    setSelected(sent);
  }

  const CHANNEL_TABS = [
    { value: '', label: 'All' },
    { value: 'email', label: 'Email' },
    { value: 'sms', label: 'SMS' },
    { value: 'call', label: 'Calls' },
  ];

  return (
    <div>
      {composeOpen && (
        <ComposeModal onClose={() => setComposeOpen(false)} onSent={handleSent} />
      )}

      <PageHeader
        title="Messages"
        subtitle="Your communication history with your advisor"
      />

      <div className="flex flex-col" style={{ height: 'calc(100vh - 200px)', minHeight: '520px' }}>

        {/* ── 2 columns ── */}
        <div className="flex flex-1 min-h-0 border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">

          {/* ── Column 1: Conversation list ── */}
          <div className="w-56 flex-shrink-0 flex flex-col border-r border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900">

            {/* Search */}
            <div className="px-2 pt-2 pb-1.5 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
              <div className="relative">
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search messages…"
                  className="input text-xs py-1.5 h-7 w-full pl-7"
                />
                <MessageSquare className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400 pointer-events-none" />
              </div>
            </div>

            {/* Channel filter */}
            <div className="flex gap-px p-2 border-b border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50 flex-wrap">
              {CHANNEL_TABS.map((t) => (
                <button key={t.value}
                  onClick={() => { setChannelFilter(t.value); setPage(1); setSelected(null); }}
                  className={`flex-1 px-1.5 py-1 rounded text-[10px] font-semibold transition-colors
                    ${channelFilter === t.value
                      ? 'bg-brand-600 text-white'
                      : 'text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700'
                    }`}>
                  {t.label}
                </button>
              ))}
            </div>

            {/* List */}
            <div className="flex-1 overflow-y-auto">
              {isLoading && [1,2,3,4,5].map(i => (
                <div key={i} className="px-3 py-3 border-b border-gray-100 dark:border-gray-800 animate-pulse flex gap-2">
                  <div className="w-8 h-8 rounded-full bg-gray-200 dark:bg-gray-700 flex-shrink-0" />
                  <div className="flex-1 space-y-1.5 py-1">
                    <div className="h-2.5 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
                    <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded w-full" />
                  </div>
                </div>
              ))}
              {!isLoading && messages.length === 0 && (
                <div className="flex flex-col items-center justify-center h-32 text-center px-4">
                  <MessageSquare className="w-6 h-6 text-gray-200 dark:text-gray-700 mb-2" />
                  <p className="text-xs text-gray-400">No messages found</p>
                </div>
              )}
              {!isLoading && messages.map((m) => (
                <ConvItem key={m.id} msg={m} selected={selected?.id === m.id} onClick={() => setSelected(m)} />
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-2 py-1.5 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-gray-800/50">
                <button className="btn-ghost p-1 text-[10px]" disabled={page === 1} onClick={() => setPage(p => p - 1)}>←</button>
                <span className="text-[10px] text-gray-400">{page}/{totalPages}</span>
                <button className="btn-ghost p-1 text-[10px]" disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>→</button>
              </div>
            )}
          </div>

          {/* ── Column 2: Message view ── */}
          <div className="flex-1 flex flex-col min-w-0">

            {/* Loading skeleton */}
            {isLoading && (
              <div className="flex-1 p-6 space-y-4 animate-pulse">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-full bg-gray-200 dark:bg-gray-700" />
                  <div className="space-y-1.5 flex-1">
                    <div className="h-3 bg-gray-200 dark:bg-gray-700 rounded w-1/3" />
                    <div className="h-2 bg-gray-100 dark:bg-gray-800 rounded w-1/4" />
                  </div>
                </div>
                <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3" />
                <div className="space-y-2">
                  <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-full" />
                  <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-5/6" />
                  <div className="h-3 bg-gray-100 dark:bg-gray-800 rounded w-4/6" />
                </div>
              </div>
            )}
            {!isLoading && <MsgView msg={selected} />}

            {/* Compose bar */}
            <div className="flex-shrink-0 border-t border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 px-4 py-2.5 flex items-center justify-between">
              <span className="text-xs text-gray-400 dark:text-gray-500">
                {totalCount} message{totalCount !== 1 ? 's' : ''}
              </span>
              <button
                onClick={() => setComposeOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-700 text-white text-xs font-semibold transition-colors shadow-sm"
              >
                <Plus className="w-3.5 h-3.5" />
                New Message
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
