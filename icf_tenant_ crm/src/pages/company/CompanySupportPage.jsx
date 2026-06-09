import { useState, useCallback, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Ticket, Plus, Kanban, List, Search, X, Send,
  Clock, AlertCircle, CheckCircle2, Loader2,
  MessageSquare, User, Tag, Flag, Calendar,
} from 'lucide-react';
import {
  getSupportTickets,
  getSupportTicketStats,
  createSupportTicket,
  getSupportTicket,
  updateTicketStatus,
  getTicketComments,
  addTicketComment,
} from '../../api/company.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import DataTable from '../../components/ui/DataTable.jsx';

// ─── Constants ────────────────────────────────────────────────────────────────

const COLUMNS = [
  { key: 'open',               label: 'Open',                  color: 'blue'   },
  { key: 'in_progress',        label: 'In Progress',           color: 'yellow' },
  { key: 'waiting_on_customer',label: 'Waiting For Customer',  color: 'purple' },
  { key: 'resolved',           label: 'Resolved',              color: 'green'  },
  { key: 'closed',             label: 'Closed',                color: 'gray'   },
];

const PRIORITY_META = {
  low:    { label: 'Low',    cls: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300' },
  normal: { label: 'Normal', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300' },
  high:   { label: 'High',   cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300' },
  urgent: { label: 'Urgent', cls: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300' },
};

const CATEGORY_META = {
  technical:       'Technical',
  billing:         'Billing',
  account:         'Account',
  feature_request: 'Feature Request',
  other:           'Other',
};

const COL_COLORS = {
  blue:   'border-blue-400 bg-blue-50 dark:bg-blue-900/10',
  yellow: 'border-yellow-400 bg-yellow-50 dark:bg-yellow-900/10',
  purple: 'border-purple-400 bg-purple-50 dark:bg-purple-900/10',
  green:  'border-green-400 bg-green-50 dark:bg-green-900/10',
  gray:   'border-gray-300 bg-gray-50 dark:bg-gray-800/40',
};

const COL_HEADER_COLORS = {
  blue:   'text-blue-700 dark:text-blue-300',
  yellow: 'text-yellow-700 dark:text-yellow-300',
  purple: 'text-purple-700 dark:text-purple-300',
  green:  'text-green-700 dark:text-green-300',
  gray:   'text-gray-500 dark:text-gray-400',
};

const STATUS_BADGE_MAP = {
  open:               'active',
  in_progress:        'pending',
  waiting_on_customer:'on_hold',
  resolved:           'verified',
  closed:             'inactive',
};

// TABLE_COLUMNS is built inside the component so renderDrawer closure is available
// (defined after setDrawerTicketId state hook)

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function fmtDateTime(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });
}

function fmtRelative(iso) {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

// ─── Summary Cards ────────────────────────────────────────────────────────────

function StatCard({ label, value, icon: Icon, colorCls, loading }) {
  return (
    <div className="card p-4 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${colorCls}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        {loading
          ? <div className="skeleton h-6 w-10 rounded mb-1" />
          : <p className="text-xl font-bold text-gray-900 dark:text-white leading-none">{value ?? 0}</p>
        }
        <p className="text-xs text-gray-500 mt-0.5">{label}</p>
      </div>
    </div>
  );
}

// ─── Priority & Category Badges ───────────────────────────────────────────────

function PriorityBadge({ priority }) {
  const meta = PRIORITY_META[priority] ?? PRIORITY_META.normal;
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${meta.cls}`}>
      <Flag className="w-2.5 h-2.5 mr-1" />
      {meta.label}
    </span>
  );
}

function CategoryBadge({ category }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-indigo-50 text-indigo-700 dark:bg-indigo-900/20 dark:text-indigo-300">
      <Tag className="w-2.5 h-2.5 mr-1" />
      {CATEGORY_META[category] ?? category}
    </span>
  );
}

// ─── Create Ticket Modal ──────────────────────────────────────────────────────

function CreateTicketModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ subject: '', body: '', priority: 'normal', category: 'other' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.subject.trim() || !form.body.trim()) {
      setError('Subject and description are required.');
      return;
    }
    setSaving(true);
    try {
      await createSupportTicket(form);
      onCreated();
    } catch {
      setError('Failed to create ticket. Please try again.');
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl w-full max-w-lg">
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-gray-100 dark:border-gray-700">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">New Support Ticket</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
            <X className="w-4 h-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {error && (
            <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300 rounded-xl text-xs">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}
          <div>
            <label className="label">Subject</label>
            <input
              value={form.subject}
              onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))}
              className="input"
              placeholder="Brief summary of the issue"
              autoFocus
            />
          </div>
          <div>
            <label className="label">Description</label>
            <textarea
              value={form.body}
              onChange={(e) => setForm((f) => ({ ...f, body: e.target.value }))}
              className="input h-28 resize-none"
              placeholder="Describe the issue in detail…"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Priority</label>
              <select value={form.priority} onChange={(e) => setForm((f) => ({ ...f, priority: e.target.value }))} className="input">
                <option value="low">Low</option>
                <option value="normal">Normal</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
            <div>
              <label className="label">Category</label>
              <select value={form.category} onChange={(e) => setForm((f) => ({ ...f, category: e.target.value }))} className="input">
                <option value="technical">Technical</option>
                <option value="billing">Billing</option>
                <option value="account">Account</option>
                <option value="feature_request">Feature Request</option>
                <option value="other">Other</option>
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-2 pt-1">
            <button type="button" onClick={onClose} className="btn-secondary btn-sm">Cancel</button>
            <button type="submit" className="btn-primary btn-sm" disabled={saving}>
              {saving ? <><Loader2 className="w-3.5 h-3.5 animate-spin" /> Submitting…</> : 'Submit Ticket'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Ticket Detail Drawer ─────────────────────────────────────────────────────

function TicketDrawer({ ticketId, onClose }) {
  const qc = useQueryClient();
  const [reply, setReply] = useState('');
  const [sending, setSending] = useState(false);
  const bottomRef = useRef(null);

  const { data: ticket, isLoading: loadingTicket } = useQuery({
    queryKey: ['support-ticket', ticketId],
    queryFn: () => getSupportTicket(ticketId),
    enabled: !!ticketId,
  });

  const { data: comments = [], isLoading: loadingComments, refetch: refetchComments } = useQuery({
    queryKey: ['ticket-comments', ticketId],
    queryFn: () => getTicketComments(ticketId),
    enabled: !!ticketId,
    refetchInterval: 15000,
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [comments.length]);

  const handleSend = async () => {
    const body = reply.trim();
    if (!body) return;
    setSending(true);
    try {
      await addTicketComment(ticketId, body);
      setReply('');
      await refetchComments();
    } catch {
      // user can retry
    } finally {
      setSending(false);
    }
  };

  const isClosed = ticket?.status === 'closed';

  return (
    <div className="fixed inset-0 z-40 flex" onClick={(e) => e.target === e.currentTarget && onClose()}>
      {/* Backdrop */}
      <div className="flex-1 bg-black/30" onClick={onClose} />

      {/* Drawer */}
      <div className="w-full max-w-xl bg-white dark:bg-gray-900 shadow-2xl flex flex-col h-full overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-700 flex-shrink-0">
          <div className="flex items-center gap-2 min-w-0">
            <Ticket className="w-4 h-4 text-gray-400 flex-shrink-0" />
            {loadingTicket
              ? <div className="skeleton h-4 w-40 rounded" />
              : <span className="text-sm font-semibold text-gray-900 dark:text-white truncate">
                  {ticket ? `#${ticket.id} — ${ticket.subject}` : 'Ticket'}
                </span>
            }
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 ml-2 flex-shrink-0">
            <X className="w-4 h-4" />
          </button>
        </div>

        {loadingTicket ? (
          <div className="flex-1 flex items-center justify-center">
            <Loader2 className="w-6 h-6 animate-spin text-gray-300" />
          </div>
        ) : ticket ? (
          <>
            {/* Metadata strip */}
            <div className="px-5 py-3 bg-gray-50 dark:bg-gray-800/40 border-b border-gray-100 dark:border-gray-700 flex-shrink-0">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <Badge
                  status={STATUS_BADGE_MAP[ticket.status] ?? 'inactive'}
                  label={ticket.status?.replace(/_/g, ' ')}
                  showDot
                />
                <PriorityBadge priority={ticket.priority} />
                <CategoryBadge category={ticket.category} />
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-400">
                <span className="flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  Created {fmtDate(ticket.created_at)}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  Updated {fmtRelative(ticket.updated_at)}
                </span>
                {ticket.assigned_to && (
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    {ticket.assigned_to_name ?? ticket.assigned_to}
                  </span>
                )}
              </div>
            </div>

            {/* Body */}
            <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700 flex-shrink-0">
              <p className="text-xs font-medium text-gray-500 mb-2">Description</p>
              <p className="text-sm text-gray-700 dark:text-gray-200 whitespace-pre-wrap">{ticket.body}</p>
            </div>

            {/* Conversation */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {loadingComments && (
                <div className="flex justify-center py-4">
                  <Loader2 className="w-5 h-5 animate-spin text-gray-300" />
                </div>
              )}
              {!loadingComments && comments.length === 0 && (
                <div className="text-center py-8">
                  <MessageSquare className="w-8 h-8 text-gray-200 dark:text-gray-700 mx-auto mb-2" />
                  <p className="text-xs text-gray-400">No replies yet.</p>
                </div>
              )}
              {comments.map((c) => {
                const initials = (c.author_name ?? '?').split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase();
                return (
                  <div key={c.id} className="flex gap-3">
                    <div className="w-7 h-7 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
                      <span className="text-[9px] font-bold text-brand-700 dark:text-brand-300">{initials}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline gap-2 mb-0.5">
                        <span className="text-[11px] font-semibold text-gray-700 dark:text-gray-200">{c.author_name}</span>
                        <span className="text-[10px] text-gray-400">{fmtDateTime(c.created_at)}</span>
                        {c.is_internal && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-yellow-100 text-yellow-700 dark:bg-yellow-900/20 dark:text-yellow-300 font-medium">Internal</span>
                        )}
                      </div>
                      <div className="bg-gray-50 dark:bg-gray-800 rounded-xl px-3 py-2">
                        <p className="text-xs text-gray-700 dark:text-gray-200 whitespace-pre-wrap">{c.body}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
              <div ref={bottomRef} />
            </div>

            {/* Reply box */}
            {!isClosed && (
              <div className="px-5 py-4 border-t border-gray-100 dark:border-gray-700 flex-shrink-0">
                <div className="flex gap-2 items-end">
                  <textarea
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
                    }}
                    placeholder="Add a reply… (Enter to send, Shift+Enter for new line)"
                    rows={2}
                    className="input flex-1 text-xs resize-none"
                  />
                  <button
                    onClick={handleSend}
                    disabled={!reply.trim() || sending}
                    className="btn-primary btn-sm flex-shrink-0 h-9"
                  >
                    {sending ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Send className="w-3.5 h-3.5" />}
                  </button>
                </div>
              </div>
            )}
            {isClosed && (
              <div className="px-5 py-3 bg-gray-50 dark:bg-gray-800/40 border-t border-gray-100 dark:border-gray-700 flex-shrink-0">
                <p className="text-xs text-gray-400 text-center">This ticket is closed.</p>
              </div>
            )}
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <p className="text-sm text-gray-400">Ticket not found.</p>
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Kanban Card ──────────────────────────────────────────────────────────────

function KanbanCard({ ticket, onOpen, onDrop, isDragOver }) {
  const handleDragStart = (e) => {
    e.dataTransfer.setData('ticketId', String(ticket.id));
    e.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      onClick={() => onOpen(ticket.id)}
      className={`
        bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-700 p-3 cursor-pointer
        shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-150 select-none
        ${isDragOver ? 'ring-2 ring-brand-500 ring-offset-1' : ''}
      `}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <span className="text-[10px] font-mono text-gray-400">#{ticket.id}</span>
        <PriorityBadge priority={ticket.priority} />
      </div>
      <p className="text-xs font-semibold text-gray-900 dark:text-white leading-snug mb-2 line-clamp-2">
        {ticket.subject}
      </p>
      <div className="flex flex-wrap gap-1 mb-2">
        <CategoryBadge category={ticket.category} />
      </div>
      <div className="flex items-center justify-between text-[10px] text-gray-400">
        <span className="flex items-center gap-1">
          <Calendar className="w-2.5 h-2.5" />
          {fmtDate(ticket.created_at)}
        </span>
        {ticket.comment_count > 0 && (
          <span className="flex items-center gap-1">
            <MessageSquare className="w-2.5 h-2.5" />
            {ticket.comment_count}
          </span>
        )}
      </div>
      {ticket.assigned_to_name && (
        <div className="mt-2 flex items-center gap-1 text-[10px] text-gray-400">
          <User className="w-2.5 h-2.5" />
          <span className="truncate">{ticket.assigned_to_name}</span>
        </div>
      )}
    </div>
  );
}

// ─── Kanban Column ────────────────────────────────────────────────────────────

function KanbanColumn({ col, tickets, onOpen, onStatusDrop }) {
  const [dragOver, setDragOver] = useState(false);

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOver(true);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const ticketId = parseInt(e.dataTransfer.getData('ticketId'), 10);
    if (ticketId) onStatusDrop(ticketId, col.key);
  };

  return (
    <div
      className={`flex flex-col rounded-2xl border-t-4 ${COL_COLORS[col.color]} min-h-[480px] flex-shrink-0 w-64`}
      onDragOver={handleDragOver}
      onDragLeave={() => setDragOver(false)}
      onDrop={handleDrop}
    >
      {/* Column header */}
      <div className="px-3 pt-3 pb-2 flex items-center gap-2">
        <span className={`text-xs font-bold tracking-wide ${COL_HEADER_COLORS[col.color]}`}>
          {col.label}
        </span>
        <span className="ml-auto text-[11px] font-semibold text-gray-400 bg-white dark:bg-gray-800 rounded-full px-2 py-0.5 shadow-sm">
          {tickets.length}
        </span>
      </div>

      {/* Cards */}
      <div
        className={`flex-1 flex flex-col gap-2 px-2 pb-3 transition-colors ${dragOver ? 'bg-white/60 dark:bg-gray-800/30 rounded-xl' : ''}`}
      >
        {tickets.length === 0 && (
          <div className="flex-1 flex items-center justify-center py-8">
            <p className="text-[11px] text-gray-300 dark:text-gray-600 text-center">No tickets</p>
          </div>
        )}
        {tickets.map((t) => (
          <KanbanCard key={t.id} ticket={t} onOpen={onOpen} onDrop={onStatusDrop} />
        ))}
      </div>
    </div>
  );
}

// ─── Filter Bar ───────────────────────────────────────────────────────────────

function FilterBar({ filters, onChange, onReset }) {
  const hasActive = filters.search || filters.category || filters.priority || filters.status || filters.date_from || filters.date_to;

  return (
    <div className="flex flex-wrap items-center gap-2 px-4 py-3 border-b border-gray-100 dark:border-gray-700 bg-gray-50/60 dark:bg-gray-800/30">
      {/* Search */}
      <div className="relative flex-1 min-w-[200px] max-w-xs">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
        <input
          type="search"
          value={filters.search}
          onChange={(e) => onChange('search', e.target.value)}
          placeholder="Search by ID or subject…"
          className="input pl-8 text-xs h-8"
        />
      </div>

      {/* Category */}
      <select
        value={filters.category}
        onChange={(e) => onChange('category', e.target.value)}
        className="text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800 h-8"
      >
        <option value="">All Categories</option>
        <option value="technical">Technical</option>
        <option value="billing">Billing</option>
        <option value="account">Account</option>
        <option value="feature_request">Feature Request</option>
        <option value="other">Other</option>
      </select>

      {/* Priority */}
      <select
        value={filters.priority}
        onChange={(e) => onChange('priority', e.target.value)}
        className="text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800 h-8"
      >
        <option value="">All Priorities</option>
        <option value="low">Low</option>
        <option value="normal">Normal</option>
        <option value="high">High</option>
        <option value="urgent">Urgent</option>
      </select>

      {/* Status (Table view filter) */}
      <select
        value={filters.status}
        onChange={(e) => onChange('status', e.target.value)}
        className="text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800 h-8"
      >
        <option value="">All Statuses</option>
        <option value="open">Open</option>
        <option value="in_progress">In Progress</option>
        <option value="waiting_on_customer">Waiting</option>
        <option value="resolved">Resolved</option>
        <option value="closed">Closed</option>
      </select>

      {/* Date from */}
      <input
        type="date"
        value={filters.date_from}
        onChange={(e) => onChange('date_from', e.target.value)}
        className="text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800 h-8"
        title="From date"
      />
      <input
        type="date"
        value={filters.date_to}
        onChange={(e) => onChange('date_to', e.target.value)}
        className="text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800 h-8"
        title="To date"
      />

      {hasActive && (
        <button
          onClick={onReset}
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-2 h-8"
        >
          <X className="w-3.5 h-3.5" />
          Clear
        </button>
      )}
    </div>
  );
}

// ─── Empty State ──────────────────────────────────────────────────────────────

function EmptyState({ onNew }) {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <div className="w-16 h-16 bg-gray-100 dark:bg-gray-800 rounded-2xl flex items-center justify-center mb-4">
        <Ticket className="w-8 h-8 text-gray-300 dark:text-gray-600" />
      </div>
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">No support tickets</h3>
      <p className="text-xs text-gray-400 max-w-xs mb-6">
        Submit a ticket when you need help from our support team. We typically respond within one business day.
      </p>
      <button onClick={onNew} className="btn-primary btn-sm">
        <Plus className="w-3.5 h-3.5" />
        Create Your First Ticket
      </button>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

const EMPTY_FILTERS = { search: '', category: '', priority: '', status: '', date_from: '', date_to: '' };

export default function CompanySupportPage() {
  const qc = useQueryClient();
  const [view, setView] = useState(() => sessionStorage.getItem('support_view') ?? 'kanban');
  const [showCreate, setShowCreate] = useState(false);
  const [drawerTicketId, setDrawerTicketId] = useState(null);
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  // Table pagination state
  const [tablePage, setTablePage] = useState(1);
  const [tablePageSize, setTablePageSize] = useState(20);
  const [tableOrdering, setTableOrdering] = useState('-created_at');

  const setViewPersisted = (v) => {
    sessionStorage.setItem('support_view', v);
    setView(v);
  };

  // Stats
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['support-ticket-stats'],
    queryFn: getSupportTicketStats,
  });

  // All tickets for Kanban (fetch all, client-side filter)
  const kanbanParams = {
    page: 1,
    page_size: 200,
    search: filters.search || undefined,
    category: filters.category || undefined,
    priority: filters.priority || undefined,
    status: filters.status || undefined,
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
  };

  const { data: kanbanData, isLoading: kanbanLoading } = useQuery({
    queryKey: ['support-tickets-kanban', kanbanParams],
    queryFn: () => getSupportTickets(kanbanParams),
    enabled: view === 'kanban',
  });

  // Table tickets (server-side)
  const tableParams = {
    page: tablePage,
    page_size: tablePageSize,
    ordering: tableOrdering,
    search: filters.search || undefined,
    category: filters.category || undefined,
    priority: filters.priority || undefined,
    status: filters.status || undefined,
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
  };

  const { data: tableData, isLoading: tableLoading } = useQuery({
    queryKey: ['support-tickets-table', tableParams],
    queryFn: () => getSupportTickets(tableParams),
    keepPreviousData: true,
    enabled: view === 'table',
  });

  const allKanbanTickets = Array.isArray(kanbanData) ? kanbanData : (kanbanData?.results ?? []);
  const tableTickets = Array.isArray(tableData) ? tableData : (tableData?.results ?? []);
  const tableTotal = Array.isArray(tableData) ? tableData.length : (tableData?.count ?? 0);

  // Group by status for Kanban
  const columnMap = {};
  COLUMNS.forEach((c) => { columnMap[c.key] = []; });
  allKanbanTickets.forEach((t) => {
    if (columnMap[t.status] !== undefined) columnMap[t.status].push(t);
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }) => updateTicketStatus(id, status),
    onMutate: async ({ id, status: newStatus }) => {
      await qc.cancelQueries({ queryKey: ['support-tickets-kanban'] });
      const prev = qc.getQueryData(['support-tickets-kanban', kanbanParams]);
      // Optimistic update
      qc.setQueryData(['support-tickets-kanban', kanbanParams], (old) => {
        if (!old) return old;
        const results = Array.isArray(old) ? old : (old.results ?? []);
        const updated = results.map((t) => t.id === id ? { ...t, status: newStatus } : t);
        return Array.isArray(old) ? updated : { ...old, results: updated };
      });
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(['support-tickets-kanban', kanbanParams], ctx.prev);
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['support-tickets-kanban'] });
      qc.invalidateQueries({ queryKey: ['support-ticket-stats'] });
    },
  });

  const handleStatusDrop = useCallback((ticketId, newStatus) => {
    const ticket = allKanbanTickets.find((t) => t.id === ticketId);
    if (!ticket || ticket.status === newStatus) return;
    updateStatusMutation.mutate({ id: ticketId, status: newStatus });
  }, [allKanbanTickets, updateStatusMutation]);

  const handleFilterChange = (key, value) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setTablePage(1);
  };

  const handleFilterReset = () => {
    setFilters(EMPTY_FILTERS);
    setTablePage(1);
  };

  const handleCreated = () => {
    setShowCreate(false);
    qc.invalidateQueries({ queryKey: ['support-tickets-kanban'] });
    qc.invalidateQueries({ queryKey: ['support-tickets-table'] });
    qc.invalidateQueries({ queryKey: ['support-ticket-stats'] });
  };

  const isEmpty = !kanbanLoading && allKanbanTickets.length === 0 && view === 'kanban' &&
    !filters.search && !filters.category && !filters.priority && !filters.status;

  // Build DataTable columns with render functions (needs setDrawerTicketId in closure)
  const tableColumns = [
    {
      key: 'id', label: '#', sortable: true,
      render: (row) => <span className="font-mono text-[11px] text-gray-500">#{row.id}</span>,
    },
    {
      key: 'subject', label: 'Subject', sortable: true,
      render: (row) => (
        <button
          onClick={() => setDrawerTicketId(row.id)}
          className="text-xs font-medium text-gray-900 dark:text-white hover:text-brand-600 dark:hover:text-brand-400 text-left max-w-[260px] truncate block"
        >
          {row.subject}
        </button>
      ),
    },
    {
      key: 'category', label: 'Category', sortable: false,
      render: (row) => <CategoryBadge category={row.category} />,
    },
    {
      key: 'priority', label: 'Priority', sortable: true,
      render: (row) => <PriorityBadge priority={row.priority} />,
    },
    {
      key: 'status', label: 'Status', sortable: true,
      render: (row) => (
        <Badge
          status={STATUS_BADGE_MAP[row.status] ?? 'inactive'}
          label={row.status?.replace(/_/g, ' ')}
          showDot
        />
      ),
    },
    {
      key: 'created_at', label: 'Created', sortable: true,
      render: (row) => <span className="text-[11px] text-gray-400">{fmtDate(row.created_at)}</span>,
    },
    {
      key: 'updated_at', label: 'Updated', sortable: true,
      render: (row) => <span className="text-[11px] text-gray-400">{fmtDate(row.updated_at)}</span>,
    },
  ];

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <PageHeader
        title="Support Center"
        subtitle="Submit and track support requests with ICF"
        icon={Ticket}
        actions={
          <div className="flex items-center gap-2">
            {/* View switcher */}
            <div className="flex items-center rounded-lg border border-gray-200 dark:border-gray-600 overflow-hidden">
              <button
                onClick={() => setViewPersisted('kanban')}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors ${
                  view === 'kanban'
                    ? 'bg-brand-600 text-white'
                    : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}
              >
                <Kanban className="w-3.5 h-3.5" />
                Kanban
              </button>
              <button
                onClick={() => setViewPersisted('table')}
                className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors border-l border-gray-200 dark:border-gray-600 ${
                  view === 'table'
                    ? 'bg-brand-600 text-white'
                    : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
                }`}
              >
                <List className="w-3.5 h-3.5" />
                Table
              </button>
            </div>

            <button onClick={() => setShowCreate(true)} className="btn-primary btn-sm">
              <Plus className="w-3.5 h-3.5" />
              Create Ticket
            </button>
          </div>
        }
      />

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <StatCard label="Total Tickets"    value={stats?.total}              icon={Ticket}        colorCls="bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-300"   loading={statsLoading} />
        <StatCard label="Open"             value={stats?.open}               icon={AlertCircle}   colorCls="bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-300"    loading={statsLoading} />
        <StatCard label="In Progress"      value={stats?.in_progress}        icon={Loader2}       colorCls="bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-300" loading={statsLoading} />
        <StatCard label="Waiting"          value={stats?.waiting}            icon={Clock}         colorCls="bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-300"  loading={statsLoading} />
        <StatCard label="Resolved This Month" value={stats?.resolved_this_month} icon={CheckCircle2} colorCls="bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-300" loading={statsLoading} />
      </div>

      {/* Main Board */}
      <div className="card overflow-hidden">
        {/* Filter bar */}
        <FilterBar filters={filters} onChange={handleFilterChange} onReset={handleFilterReset} />

        {/* ── Kanban View ── */}
        {view === 'kanban' && (
          <>
            {kanbanLoading && (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-7 h-7 animate-spin text-gray-300" />
              </div>
            )}
            {!kanbanLoading && isEmpty && <EmptyState onNew={() => setShowCreate(true)} />}
            {!kanbanLoading && !isEmpty && (
              <div className="overflow-x-auto">
                <div className="flex gap-3 p-4 min-w-max">
                  {COLUMNS.map((col) => (
                    <KanbanColumn
                      key={col.key}
                      col={col}
                      tickets={columnMap[col.key] ?? []}
                      onOpen={setDrawerTicketId}
                      onStatusDrop={handleStatusDrop}
                    />
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* ── Table View ── */}
        {view === 'table' && (
          <DataTable
            columns={tableColumns}
            data={tableTickets}
            totalCount={tableTotal}
            page={tablePage}
            pageSize={tablePageSize}
            loading={tableLoading}
            ordering={tableOrdering}
            onPageChange={setTablePage}
            onPageSizeChange={(s) => { setTablePageSize(s); setTablePage(1); }}
            onSort={(ord) => { setTableOrdering(ord); setTablePage(1); }}
            emptyText="No tickets match your filters."
          />
        )}
      </div>

      {/* Modals / Drawers */}
      {showCreate && (
        <CreateTicketModal
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
        />
      )}

      {drawerTicketId && (
        <TicketDrawer
          ticketId={drawerTicketId}
          onClose={() => setDrawerTicketId(null)}
        />
      )}
    </div>
  );
}
