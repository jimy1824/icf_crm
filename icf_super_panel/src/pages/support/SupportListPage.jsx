import { useState, useCallback, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import {
  Ticket, Plus, Kanban, List, Search, X, Send,
  Clock, AlertCircle, CheckCircle2, Loader2,
  MessageSquare, User, Tag, Flag, Calendar,
  Lock, Building2, UserCheck,
} from 'lucide-react';
import { supportApi } from '../../api/support.js';
import { tenantsApi } from '../../api/tenants.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import DataTable from '../../components/ui/DataTable.jsx';
import { useAuth } from '../../context/AuthContext.jsx';

// ─── Constants ────────────────────────────────────────────────────────────────

const COLUMNS = [
  { key: 'open',                label: 'Open',               color: 'blue'   },
  { key: 'in_progress',         label: 'In Progress',        color: 'violet' },
  { key: 'waiting_on_customer', label: 'Waiting For Customer', color: 'purple' },
  { key: 'resolved',            label: 'Resolved',           color: 'green'  },
  { key: 'closed',              label: 'Closed',             color: 'gray'   },
];

const VALID_TRANSITIONS = {
  open:                ['in_progress', 'waiting_on_customer', 'resolved', 'closed'],
  in_progress:         ['waiting_on_customer', 'resolved', 'closed'],
  waiting_on_customer: ['in_progress', 'resolved', 'closed'],
  resolved:            ['open', 'closed'],
  closed:              [],
};

const TRANSITION_LABELS = {
  open:                'Reopen',
  in_progress:         'In Progress',
  waiting_on_customer: 'Waiting',
  resolved:            'Resolve',
  closed:              'Close',
};

const PRIORITY_META = {
  low:    { label: 'Low',    cls: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300' },
  normal: { label: 'Normal', cls: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' },
  high:   { label: 'High',   cls: 'bg-orange-100 text-orange-700 dark:bg-orange-900/40 dark:text-orange-300' },
  urgent: { label: 'Urgent', cls: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300' },
};

const CATEGORY_LABELS = {
  technical:       'Technical',
  billing:         'Billing',
  account:         'Account',
  feature_request: 'Feature Request',
  other:           'Other',
};

const COL_COLORS = {
  blue:   'border-blue-400 bg-blue-50 dark:bg-blue-900/20',
  violet: 'border-violet-400 bg-violet-50 dark:bg-violet-900/20',
  purple: 'border-purple-400 bg-purple-50 dark:bg-purple-900/20',
  green:  'border-green-400 bg-green-50 dark:bg-green-900/20',
  gray:   'border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-800/40',
};

const COL_HEADER_COLORS = {
  blue:   'text-blue-700 dark:text-blue-400',
  violet: 'text-violet-700 dark:text-violet-400',
  purple: 'text-purple-700 dark:text-purple-400',
  green:  'text-green-700 dark:text-green-400',
  gray:   'text-gray-500 dark:text-gray-400',
};

const EMPTY_FILTERS = {
  search: '', category: '', priority: '', status: '',
  assigned_to: '', tenant_id: '', date_from: '', date_to: '',
};

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
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-indigo-50 text-indigo-700 dark:bg-indigo-900/40 dark:text-indigo-300">
      <Tag className="w-2.5 h-2.5 mr-1" />
      {CATEGORY_LABELS[category] ?? category}
    </span>
  );
}

// ─── Stat Card ────────────────────────────────────────────────────────────────

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
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{label}</p>
      </div>
    </div>
  );
}

// ─── Searchable Staff Dropdown ────────────────────────────────────────────────

function StaffDropdown({ value, onChange, staff = [] }) {
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  const selected = staff.find((s) => String(s.id) === String(value));
  const filtered = staff.filter((s) =>
    !query || s.name.toLowerCase().includes(query.toLowerCase()) || s.email.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    const handler = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const select = (id) => { onChange(id); setOpen(false); setQuery(''); };

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2.5 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 h-8 min-w-[160px] max-w-[220px]"
      >
        <UserCheck className="w-3 h-3 text-gray-400 flex-shrink-0" />
        <span className="truncate text-left flex-1">
          {selected ? selected.name : 'All Assignments'}
        </span>
        {value && (
          <span
            className="text-gray-300 dark:text-gray-500 hover:text-gray-500 dark:hover:text-gray-300 ml-1"
            onClick={(e) => { e.stopPropagation(); select(''); }}
          >×</span>
        )}
      </button>
      {open && (
        <div className="absolute z-50 top-full left-0 mt-1 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 rounded-xl shadow-lg overflow-hidden">
          <div className="p-2 border-b border-gray-100 dark:border-gray-700">
            <div className="relative">
              <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
              <input
                autoFocus
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Search staff…"
                className="w-full pl-6 pr-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-500"
              />
            </div>
          </div>
          <div className="max-h-52 overflow-y-auto">
            <button
              onClick={() => select('')}
              className={`w-full text-left px-3 py-2 text-xs hover:bg-gray-50 dark:hover:bg-gray-700 ${!value ? 'font-semibold text-brand-600' : 'text-gray-600 dark:text-gray-300'}`}
            >
              All Assignments
            </button>
            <button
              onClick={() => select('me')}
              className={`w-full text-left px-3 py-2 text-xs hover:bg-gray-50 dark:hover:bg-gray-700 ${value === 'me' ? 'font-semibold text-brand-600' : 'text-gray-600 dark:text-gray-300'}`}
            >
              Assigned to Me
            </button>
            <button
              onClick={() => select('unassigned')}
              className={`w-full text-left px-3 py-2 text-xs hover:bg-gray-50 dark:hover:bg-gray-700 ${value === 'unassigned' ? 'font-semibold text-brand-600' : 'text-gray-600 dark:text-gray-300'}`}
            >
              Unassigned
            </button>
            {filtered.length > 0 && <div className="border-t border-gray-100 dark:border-gray-700 mt-1 pt-1" />}
            {filtered.map((s) => (
              <button
                key={s.id}
                onClick={() => select(String(s.id))}
                className={`w-full text-left px-3 py-2 text-xs hover:bg-gray-50 dark:hover:bg-gray-700 ${String(value) === String(s.id) ? 'font-semibold text-brand-600' : 'text-gray-700 dark:text-gray-300'}`}
              >
                <span className="block font-medium">{s.name}</span>
                <span className="block text-[10px] text-gray-400">{s.email}</span>
              </button>
            ))}
            {filtered.length === 0 && query && (
              <p className="px-3 py-2 text-xs text-gray-400">No staff found</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Filter Bar ───────────────────────────────────────────────────────────────

function FilterBar({ filters, onChange, onReset, tenants = [], staff = [] }) {
  const hasActive = Object.values(filters).some(Boolean);
  const selectCls = 'text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 h-8';
  return (
    <div className="flex flex-wrap items-center gap-2 px-4 py-3 border-b border-gray-100 dark:border-gray-700 bg-gray-50/60 dark:bg-gray-800/40">
      {/* Search */}
      <div className="relative flex-1 min-w-[180px] max-w-xs">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
        <input
          type="search"
          value={filters.search}
          onChange={(e) => onChange('search', e.target.value)}
          placeholder="ID, subject, or company…"
          className="input pl-8 text-xs h-8"
        />
      </div>

      <select
        value={filters.tenant_id}
        onChange={(e) => onChange('tenant_id', e.target.value)}
        className={`${selectCls} max-w-[180px]`}
      >
        <option value="">All Companies</option>
        {tenants.map((t) => (
          <option key={t.id} value={t.id}>{t.firm_name}</option>
        ))}
      </select>

      <select value={filters.category} onChange={(e) => onChange('category', e.target.value)} className={selectCls}>
        <option value="">All Categories</option>
        <option value="technical">Technical</option>
        <option value="billing">Billing</option>
        <option value="account">Account</option>
        <option value="feature_request">Feature Request</option>
        <option value="other">Other</option>
      </select>

      <select value={filters.priority} onChange={(e) => onChange('priority', e.target.value)} className={selectCls}>
        <option value="">All Priorities</option>
        <option value="low">Low</option>
        <option value="normal">Normal</option>
        <option value="high">High</option>
        <option value="urgent">Urgent</option>
      </select>

      <select value={filters.status} onChange={(e) => onChange('status', e.target.value)} className={selectCls}>
        <option value="">All Statuses</option>
        <option value="open">Open</option>
        <option value="in_progress">In Progress</option>
        <option value="waiting_on_customer">Waiting</option>
        <option value="resolved">Resolved</option>
        <option value="closed">Closed</option>
      </select>

      <StaffDropdown
        value={filters.assigned_to}
        onChange={(v) => onChange('assigned_to', v)}
        staff={staff}
      />

      <input type="date" value={filters.date_from} onChange={(e) => onChange('date_from', e.target.value)}
        className={selectCls} title="From date" />
      <input type="date" value={filters.date_to} onChange={(e) => onChange('date_to', e.target.value)}
        className={selectCls} title="To date" />

      {hasActive && (
        <button onClick={onReset} className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 px-2 h-8">
          <X className="w-3.5 h-3.5" />
          Clear
        </button>
      )}
    </div>
  );
}

// ─── Kanban Card ──────────────────────────────────────────────────────────────

function KanbanCard({ ticket, onOpen }) {
  const handleDragStart = (e) => {
    e.dataTransfer.setData('ticketId', String(ticket.id));
    e.dataTransfer.effectAllowed = 'move';
  };

  return (
    <div
      draggable
      onDragStart={handleDragStart}
      onClick={() => onOpen(ticket.id)}
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-100 dark:border-gray-700 p-3 cursor-pointer shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-150 select-none"
    >
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <span className="text-[10px] font-mono text-gray-400 dark:text-gray-500">#{ticket.id}</span>
        <PriorityBadge priority={ticket.priority} />
      </div>

      {ticket.tenant_name && (
        <div className="flex items-center gap-1 mb-1.5">
          <Building2 className="w-2.5 h-2.5 text-gray-400 flex-shrink-0" />
          <span className="text-[10px] font-semibold text-brand-600 dark:text-brand-400 truncate">{ticket.tenant_name}</span>
        </div>
      )}

      <p className="text-xs font-semibold text-gray-900 dark:text-gray-100 leading-snug mb-2 line-clamp-2">
        {ticket.subject}
      </p>
      <div className="flex flex-wrap gap-1 mb-2">
        <CategoryBadge category={ticket.category} />
      </div>
      <div className="flex items-center justify-between text-[10px] text-gray-400 dark:text-gray-500">
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
        <div className="mt-2 flex items-center gap-1 text-[10px] text-gray-400 dark:text-gray-500">
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

  return (
    <div
      className={`flex flex-col rounded-2xl border-t-4 ${COL_COLORS[col.color]} min-h-[480px] flex-shrink-0 w-64`}
      onDragOver={(e) => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; setDragOver(true); }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        const id = parseInt(e.dataTransfer.getData('ticketId'), 10);
        if (id) onStatusDrop(id, col.key);
      }}
    >
      <div className="px-3 pt-3 pb-2 flex items-center gap-2">
        <span className={`text-xs font-bold tracking-wide ${COL_HEADER_COLORS[col.color]}`}>
          {col.label}
        </span>
        <span className="ml-auto text-[11px] font-semibold text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-700 rounded-full px-2 py-0.5 shadow-sm">
          {tickets.length}
        </span>
      </div>
      <div className={`flex-1 flex flex-col gap-2 px-2 pb-3 transition-colors ${dragOver ? 'bg-white/30 dark:bg-white/10 rounded-xl' : ''}`}>
        {tickets.length === 0 && (
          <div className="flex-1 flex items-center justify-center py-8">
            <p className="text-[11px] text-gray-300 dark:text-gray-600 text-center">No tickets</p>
          </div>
        )}
        {tickets.map((t) => (
          <KanbanCard key={t.id} ticket={t} onOpen={onOpen} />
        ))}
      </div>
    </div>
  );
}

// ─── Ticket Detail Drawer ─────────────────────────────────────────────────────

function TicketDrawer({ ticketId, onClose, onStatusChanged, staff = [] }) {
  const qc = useQueryClient();
  const { user } = useAuth();
  const [reply, setReply] = useState('');
  const [isInternal, setIsInternal] = useState(false);
  const [sending, setSending] = useState(false);
  const [assigneeId, setAssigneeId] = useState('');
  const [assignQuery, setAssignQuery] = useState('');
  const [assigning, setAssigning] = useState(false);
  const [transitioning, setTransitioning] = useState(null);
  const [showAssign, setShowAssign] = useState(false);
  const assignRef = useRef(null);
  const bottomRef = useRef(null);

  const { data: ticket, isLoading: loadingTicket } = useQuery({
    queryKey: ['support-ticket', ticketId],
    queryFn: () => supportApi.getTicket(ticketId),
    enabled: !!ticketId,
  });

  const { data: comments = [], isLoading: loadingComments, refetch: refetchComments } = useQuery({
    queryKey: ['ticket-comments', ticketId],
    queryFn: () => supportApi.getComments(ticketId),
    enabled: !!ticketId,
    refetchInterval: 20_000,
  });

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [comments.length]);

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['support-ticket', ticketId] });
    qc.invalidateQueries({ queryKey: ['ticket-comments', ticketId] });
    qc.invalidateQueries({ queryKey: ['support-tickets-kanban'] });
    qc.invalidateQueries({ queryKey: ['support-tickets-table'] });
    qc.invalidateQueries({ queryKey: ['support-ticket-stats'] });
  };

  const handleSend = async () => {
    const body = reply.trim();
    if (!body) return;
    setSending(true);
    try {
      await supportApi.addComment(ticketId, body, isInternal);
      setReply('');
      setIsInternal(false);
      await refetchComments();
    } finally {
      setSending(false);
    }
  };

  const handleTransition = async (newStatus) => {
    setTransitioning(newStatus);
    try {
      await supportApi.transitionStatus(ticketId, newStatus);
      invalidate();
      onStatusChanged?.();
    } finally {
      setTransitioning(null);
    }
  };

  const handleAssign = async (id) => {
    const targetId = id ?? assigneeId;
    if (!targetId) return;
    setAssigning(true);
    try {
      await supportApi.assignTicket(ticketId, parseInt(targetId, 10));
      setShowAssign(false);
      setAssigneeId('');
      setAssignQuery('');
      invalidate();
    } finally {
      setAssigning(false);
    }
  };

  const filteredStaff = staff.filter((s) =>
    !assignQuery || s.name.toLowerCase().includes(assignQuery.toLowerCase()) || s.email.toLowerCase().includes(assignQuery.toLowerCase())
  );

  const isClosed = ticket?.status === 'closed';
  const transitions = VALID_TRANSITIONS[ticket?.status] ?? [];
  const isStaff = user?.role === 'super_admin' || user?.role === 'support';

  return (
    <div className="fixed inset-0 z-40 flex" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="flex-1 bg-black/30" onClick={onClose} />

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
            <div className="px-5 py-3 bg-gray-50 dark:bg-gray-800/60 border-b border-gray-100 dark:border-gray-700 flex-shrink-0 space-y-2">
              {ticket.tenant_name && (
                <div className="flex items-center gap-1.5">
                  <Building2 className="w-3.5 h-3.5 text-gray-400" />
                  <span className="text-xs font-semibold text-brand-700 dark:text-brand-400">{ticket.tenant_name}</span>
                </div>
              )}
              <div className="flex flex-wrap items-center gap-2">
                <Badge status={ticket.status} showDot />
                <PriorityBadge priority={ticket.priority} />
                <CategoryBadge category={ticket.category} />
              </div>
              <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] text-gray-400 dark:text-gray-500">
                <span className="flex items-center gap-1">
                  <User className="w-3 h-3" />
                  {ticket.created_by_name ?? 'Unknown'}
                </span>
                <span className="flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  {fmtDate(ticket.created_at)}
                </span>
                <span className="flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {fmtRelative(ticket.updated_at)}
                </span>
                {ticket.assigned_to_name && (
                  <span className="flex items-center gap-1">
                    <UserCheck className="w-3 h-3" />
                    {ticket.assigned_to_name}
                  </span>
                )}
              </div>

              {isStaff && (
                <div className="flex flex-wrap items-center gap-2 pt-1">
                  {transitions.map((s) => (
                    <button
                      key={s}
                      onClick={() => handleTransition(s)}
                      disabled={!!transitioning}
                      className={`px-2.5 py-1 rounded-lg text-[11px] font-medium border transition-colors disabled:opacity-60 ${
                        s === 'closed' || s === 'resolved'
                          ? 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:border-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-400 dark:hover:bg-emerald-900/50'
                          : s === 'open'
                          ? 'border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100 dark:border-blue-800 dark:bg-blue-900/30 dark:text-blue-400 dark:hover:bg-blue-900/50'
                          : 'border-gray-200 bg-white text-gray-700 hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
                      }`}
                    >
                      {transitioning === s ? <Loader2 className="w-3 h-3 animate-spin inline" /> : TRANSITION_LABELS[s]}
                    </button>
                  ))}
                  <button
                    onClick={() => setShowAssign((v) => !v)}
                    className="px-2.5 py-1 rounded-lg text-[11px] font-medium border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-600 flex items-center gap-1"
                  >
                    <UserCheck className="w-3 h-3" />
                    Assign
                  </button>
                </div>
              )}

              {showAssign && (
                <div ref={assignRef} className="pt-1">
                  <div className="border border-gray-200 dark:border-gray-600 rounded-xl overflow-hidden bg-white dark:bg-gray-800 shadow-sm">
                    <div className="p-2 border-b border-gray-100 dark:border-gray-700">
                      <div className="relative">
                        <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3 text-gray-400" />
                        <input
                          autoFocus
                          type="text"
                          value={assignQuery}
                          onChange={(e) => setAssignQuery(e.target.value)}
                          placeholder="Search support staff…"
                          className="w-full pl-6 pr-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-brand-500"
                        />
                      </div>
                    </div>
                    <div className="max-h-44 overflow-y-auto">
                      {filteredStaff.length === 0 && (
                        <p className="px-3 py-3 text-xs text-gray-400 text-center">
                          {staff.length === 0 ? 'Loading staff…' : 'No staff match'}
                        </p>
                      )}
                      {filteredStaff.map((s) => (
                        <button
                          key={s.id}
                          onClick={() => handleAssign(s.id)}
                          disabled={assigning}
                          className="w-full text-left px-3 py-2 text-xs hover:bg-brand-50 dark:hover:bg-brand-900/20 flex items-center justify-between disabled:opacity-60"
                        >
                          <div>
                            <span className="block font-medium text-gray-800 dark:text-gray-200">{s.name}</span>
                            <span className="block text-[10px] text-gray-400">{s.email} · {s.role}</span>
                          </div>
                          {assigning && assigneeId === String(s.id)
                            ? <Loader2 className="w-3 h-3 animate-spin text-brand-500" />
                            : <UserCheck className="w-3 h-3 text-gray-300 dark:text-gray-600" />
                          }
                        </button>
                      ))}
                    </div>
                  </div>
                  <button
                    onClick={() => { setShowAssign(false); setAssignQuery(''); }}
                    className="mt-1 text-[11px] text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 flex items-center gap-1"
                  >
                    <X className="w-3 h-3" /> Cancel
                  </button>
                </div>
              )}
            </div>

            {/* Body */}
            <div className="px-5 py-4 border-b border-gray-100 dark:border-gray-700 flex-shrink-0">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">Description</p>
              <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{ticket.body}</p>
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
                  <div key={c.id} className={`flex gap-3 ${c.is_internal ? 'opacity-90' : ''}`}>
                    <div className={`w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0 ${
                      c.is_internal ? 'bg-yellow-100 dark:bg-yellow-900/40' : 'bg-brand-100 dark:bg-brand-900/40'
                    }`}>
                      {c.is_internal
                        ? <Lock className="w-3 h-3 text-yellow-600 dark:text-yellow-400" />
                        : <span className="text-[9px] font-bold text-brand-700 dark:text-brand-300">{initials}</span>
                      }
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline gap-2 mb-0.5">
                        <span className="text-[11px] font-semibold text-gray-700 dark:text-gray-300">{c.author_name}</span>
                        <span className="text-[10px] text-gray-400">{fmtDateTime(c.created_at)}</span>
                        {c.is_internal && (
                          <span className="text-[9px] px-1.5 py-0.5 rounded bg-yellow-100 dark:bg-yellow-900/40 text-yellow-700 dark:text-yellow-400 font-medium flex items-center gap-0.5">
                            <Lock className="w-2 h-2" /> Internal
                          </span>
                        )}
                      </div>
                      <div className={`rounded-xl px-3 py-2 ${
                        c.is_internal
                          ? 'bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-100 dark:border-yellow-800'
                          : 'bg-gray-50 dark:bg-gray-800'
                      }`}>
                        <p className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap">{c.body}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
              <div ref={bottomRef} />
            </div>

            {/* Reply box */}
            {!isClosed ? (
              <div className="px-5 py-4 border-t border-gray-100 dark:border-gray-700 flex-shrink-0">
                {isStaff && (
                  <div className="flex items-center gap-2 mb-2">
                    <button
                      onClick={() => setIsInternal((v) => !v)}
                      className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[11px] font-medium border transition-colors ${
                        isInternal
                          ? 'bg-yellow-50 dark:bg-yellow-900/30 border-yellow-200 dark:border-yellow-800 text-yellow-700 dark:text-yellow-400'
                          : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-600 text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
                      }`}
                    >
                      <Lock className="w-3 h-3" />
                      {isInternal ? 'Internal Note' : 'Public Reply'}
                    </button>
                    <span className="text-[10px] text-gray-400">
                      {isInternal ? 'Hidden from tenant' : 'Visible to tenant'}
                    </span>
                  </div>
                )}
                <div className="flex gap-2 items-end">
                  <textarea
                    value={reply}
                    onChange={(e) => setReply(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
                    }}
                    placeholder={isInternal ? 'Add an internal note… (hidden from tenant)' : 'Reply to tenant… (Enter to send)'}
                    rows={2}
                    className={`input flex-1 text-xs resize-none ${
                      isInternal ? 'border-yellow-200 dark:border-yellow-800 bg-yellow-50/50 dark:bg-yellow-900/20' : ''
                    }`}
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
            ) : (
              <div className="px-5 py-3 bg-gray-50 dark:bg-gray-800/60 border-t border-gray-100 dark:border-gray-700 flex-shrink-0">
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

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function SupportListPage() {
  const qc = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [view, setView] = useState(() => sessionStorage.getItem('sp_support_view') ?? 'kanban');
  const [drawerTicketId, setDrawerTicketId] = useState(null);
  const [filters, setFilters] = useState(EMPTY_FILTERS);

  useEffect(() => {
    const ticketParam = searchParams.get('ticket');
    if (ticketParam) {
      setDrawerTicketId(parseInt(ticketParam, 10));
      setSearchParams({}, { replace: true });
    }
  }, []);
  const [tablePage, setTablePage] = useState(1);
  const [tablePageSize, setTablePageSize] = useState(20);
  const [tableOrdering, setTableOrdering] = useState('-created_at');

  const setViewPersisted = (v) => {
    sessionStorage.setItem('sp_support_view', v);
    setView(v);
  };

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['support-ticket-stats'],
    queryFn: () => supportApi.getStats(),
  });

  const { data: staff = [] } = useQuery({
    queryKey: ['support-staff'],
    queryFn: () => supportApi.listStaff(),
    staleTime: 5 * 60 * 1000,
  });

  const { data: tenantsData = [] } = useQuery({
    queryKey: ['tenants-list'],
    queryFn: () => tenantsApi.list(),
    staleTime: 5 * 60 * 1000,
  });
  const tenants = Array.isArray(tenantsData) ? tenantsData : (tenantsData?.results ?? []);

  const resolvedAssignedTo = filters.assigned_to || undefined;

  const kanbanParams = {
    page: 1, page_size: 200,
    search:      filters.search     || undefined,
    category:    filters.category   || undefined,
    priority:    filters.priority   || undefined,
    status:      filters.status     || undefined,
    assigned_to: resolvedAssignedTo,
    tenant_id:   filters.tenant_id  || undefined,
    date_from:   filters.date_from  || undefined,
    date_to:     filters.date_to    || undefined,
  };

  const { data: kanbanData, isLoading: kanbanLoading } = useQuery({
    queryKey: ['support-tickets-kanban', kanbanParams],
    queryFn: () => supportApi.listTickets(kanbanParams),
    enabled: view === 'kanban',
  });

  const tableParams = {
    page: tablePage, page_size: tablePageSize, ordering: tableOrdering,
    search:      filters.search     || undefined,
    category:    filters.category   || undefined,
    priority:    filters.priority   || undefined,
    status:      filters.status     || undefined,
    assigned_to: resolvedAssignedTo,
    tenant_id:   filters.tenant_id  || undefined,
    date_from:   filters.date_from  || undefined,
    date_to:     filters.date_to    || undefined,
  };

  const { data: tableData, isLoading: tableLoading } = useQuery({
    queryKey: ['support-tickets-table', tableParams],
    queryFn: () => supportApi.listTickets(tableParams),
    keepPreviousData: true,
    enabled: view === 'table',
  });

  const allKanbanTickets = kanbanData?.results ?? (Array.isArray(kanbanData) ? kanbanData : []);
  const tableTickets = tableData?.results ?? (Array.isArray(tableData) ? tableData : []);
  const tableTotal = tableData?.count ?? 0;

  const columnMap = {};
  COLUMNS.forEach((c) => { columnMap[c.key] = []; });
  allKanbanTickets.forEach((t) => {
    if (columnMap[t.status] !== undefined) columnMap[t.status].push(t);
  });

  const updateStatusMutation = useMutation({
    mutationFn: ({ id, status }) => supportApi.transitionStatus(id, status),
    onMutate: async ({ id, status: newStatus }) => {
      await qc.cancelQueries({ queryKey: ['support-tickets-kanban'] });
      const prev = qc.getQueryData(['support-tickets-kanban', kanbanParams]);
      qc.setQueryData(['support-tickets-kanban', kanbanParams], (old) => {
        if (!old) return old;
        const results = old.results ?? (Array.isArray(old) ? old : []);
        const updated = results.map((t) => t.id === id ? { ...t, status: newStatus } : t);
        return old.results !== undefined ? { ...old, results: updated } : updated;
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
    if (!VALID_TRANSITIONS[ticket.status]?.includes(newStatus)) return;
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

  const invalidateAll = () => {
    qc.invalidateQueries({ queryKey: ['support-tickets-kanban'] });
    qc.invalidateQueries({ queryKey: ['support-tickets-table'] });
    qc.invalidateQueries({ queryKey: ['support-ticket-stats'] });
  };

  const isEmpty = !kanbanLoading && allKanbanTickets.length === 0 && view === 'kanban'
    && !Object.values(filters).some(Boolean);

  const tableColumns = [
    {
      key: 'id', label: '#', sortable: true,
      render: (row) => (
        <button onClick={() => setDrawerTicketId(row.id)} className="font-mono text-[11px] text-brand-600 dark:text-brand-400 hover:underline">
          #{row.id}
        </button>
      ),
    },
    {
      key: 'tenant_name', label: 'Company', sortable: false,
      render: (row) => (
        <div className="flex items-center gap-1 text-xs font-medium text-gray-700 dark:text-gray-300">
          <Building2 className="w-3 h-3 text-gray-400 flex-shrink-0" />
          {row.tenant_name ?? '—'}
        </div>
      ),
    },
    {
      key: 'subject', label: 'Subject', sortable: true,
      render: (row) => (
        <button
          onClick={() => setDrawerTicketId(row.id)}
          className="text-xs font-medium text-gray-900 dark:text-gray-100 hover:text-brand-600 dark:hover:text-brand-400 text-left max-w-[200px] truncate block"
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
      render: (row) => <Badge status={row.status} showDot />,
    },
    {
      key: 'assigned_to_name', label: 'Assigned To', sortable: false,
      render: (row) => (
        <span className="text-[11px] text-gray-500 dark:text-gray-400">
          {row.assigned_to_name ?? <span className="text-gray-300 dark:text-gray-600">Unassigned</span>}
        </span>
      ),
    },
    {
      key: 'comment_count', label: 'Messages', sortable: false,
      render: (row) => (
        <span className="flex items-center gap-1 text-[11px] text-gray-400 dark:text-gray-500">
          <MessageSquare className="w-3 h-3" />
          {row.comment_count}
        </span>
      ),
    },
    {
      key: 'created_at', label: 'Created', sortable: true,
      render: (row) => <span className="text-[11px] text-gray-400 dark:text-gray-500">{fmtDate(row.created_at)}</span>,
    },
    {
      key: 'updated_at', label: 'Updated', sortable: true,
      render: (row) => <span className="text-[11px] text-gray-400 dark:text-gray-500">{fmtDate(row.updated_at)}</span>,
    },
  ];

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <PageHeader
        title="Ticket Center"
        subtitle="Manage and resolve support tickets from all tenants."
        icon={Ticket}
        actions={
          <div className="flex items-center rounded-lg border border-gray-200 dark:border-gray-600 overflow-hidden">
            <button
              onClick={() => setViewPersisted('kanban')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium transition-colors ${
                view === 'kanban' ? 'bg-brand-600 text-white' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              <Kanban className="w-3.5 h-3.5" />
              Kanban
            </button>
            <button
              onClick={() => setViewPersisted('table')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium border-l border-gray-200 dark:border-gray-600 transition-colors ${
                view === 'table' ? 'bg-brand-600 text-white' : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
            >
              <List className="w-3.5 h-3.5" />
              Table
            </button>
          </div>
        }
      />

      {/* KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Total"       value={stats?.total}               icon={Ticket}        colorCls="bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-300"       loading={statsLoading} />
        <StatCard label="Open"        value={stats?.open}                icon={AlertCircle}   colorCls="bg-blue-100 dark:bg-blue-900/40 text-blue-600 dark:text-blue-400"    loading={statsLoading} />
        <StatCard label="In Progress" value={stats?.in_progress}         icon={Loader2}       colorCls="bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-400" loading={statsLoading} />
        <StatCard label="Waiting"     value={stats?.waiting}             icon={Clock}         colorCls="bg-purple-100 dark:bg-purple-900/40 text-purple-600 dark:text-purple-400" loading={statsLoading} />
        <StatCard label="Resolved"    value={stats?.resolved}            icon={CheckCircle2}  colorCls="bg-green-100 dark:bg-green-900/40 text-green-600 dark:text-green-400"  loading={statsLoading} />
        <StatCard label="Resolved/Mo" value={stats?.resolved_this_month} icon={CheckCircle2}  colorCls="bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400" loading={statsLoading} />
      </div>

      {/* Main Board */}
      <div className="card overflow-hidden">
        <FilterBar filters={filters} onChange={handleFilterChange} onReset={handleFilterReset} tenants={tenants} staff={staff} />

        {/* ── Kanban View ── */}
        {view === 'kanban' && (
          <>
            {kanbanLoading && (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-7 h-7 animate-spin text-gray-300" />
              </div>
            )}
            {!kanbanLoading && isEmpty && (
              <div className="flex flex-col items-center justify-center py-20 text-center">
                <Ticket className="w-10 h-10 text-gray-200 dark:text-gray-700 mb-3" />
                <p className="text-sm font-semibold text-gray-400">No tickets yet</p>
              </div>
            )}
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

      {/* Drawer */}
      {drawerTicketId && (
        <TicketDrawer
          ticketId={drawerTicketId}
          onClose={() => setDrawerTicketId(null)}
          onStatusChanged={invalidateAll}
          staff={staff}
        />
      )}
    </div>
  );
}
