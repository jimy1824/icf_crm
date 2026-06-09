import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Users, UserCheck, UserX, ShieldCheck, Headphones,
  Plus, X, MoreVertical, Eye, EyeOff,
} from 'lucide-react';
import DataTable from '../../components/ui/DataTable.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { staffApi } from '../../api/staff.js';
import { useAuth } from '../../context/AuthContext.jsx';

const ROLE_LABELS = {
  super_admin: 'Super Admin',
  support: 'Support',
  compliance_officer: 'Compliance Officer',
};

const ROLE_BADGE_STATUS = {
  super_admin: 'open',
  support: 'in_progress',
  compliance_officer: 'normal',
};

function RoleBadge({ role }) {
  return (
    <Badge
      status={ROLE_BADGE_STATUS[role] ?? 'default'}
      label={ROLE_LABELS[role] ?? role}
    />
  );
}

function StatCard({ label, value, icon: Icon, lightCls, darkCls }) {
  return (
    <div className="card p-4 flex items-center gap-4">
      <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${lightCls} ${darkCls}`}>
        <Icon className="w-5 h-5" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900 dark:text-white leading-none">{value ?? '—'}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{label}</p>
      </div>
    </div>
  );
}

function InviteModal({ onClose, onSuccess }) {
  const [form, setForm] = useState({
    first_name: '', last_name: '', email: '', role: 'support', password: '',
  });
  const [showPw, setShowPw] = useState(false);
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: () => staffApi.create(form),
    onSuccess: () => { onSuccess(); onClose(); },
    onError: (e) => setError(e.data?.detail || e.message || 'Failed to create staff member.'),
  });

  function set(field, val) {
    setForm((f) => ({ ...f, [field]: val }));
    setError('');
  }

  function handleSubmit(e) {
    e.preventDefault();
    if (!form.email || !form.first_name || !form.last_name || !form.password) {
      setError('All fields are required.');
      return;
    }
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }
    mutation.mutate();
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-modal border border-gray-100 dark:border-gray-700 w-full max-w-md mx-4 overflow-hidden">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-700">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Add Staff Member</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400 dark:text-gray-500"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="px-6 py-5 space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">First Name</label>
              <input className="input" value={form.first_name} onChange={(e) => set('first_name', e.target.value)} placeholder="Jane" />
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Last Name</label>
              <input className="input" value={form.last_name} onChange={(e) => set('last_name', e.target.value)} placeholder="Smith" />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Email</label>
            <input type="email" className="input" value={form.email} onChange={(e) => set('email', e.target.value)} placeholder="jane@iclosefaster.com" />
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Role</label>
            <select className="select" value={form.role} onChange={(e) => set('role', e.target.value)}>
              <option value="support">Support</option>
              <option value="compliance_officer">Compliance Officer</option>
              <option value="super_admin">Super Admin</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-gray-600 dark:text-gray-400 mb-1">Temporary Password</label>
            <div className="relative">
              <input
                type={showPw ? 'text' : 'password'}
                className="input pr-10"
                value={form.password}
                onChange={(e) => set('password', e.target.value)}
                placeholder="Min. 8 characters"
              />
              <button
                type="button"
                onClick={() => setShowPw((s) => !s)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                {showPw ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn-ghost">Cancel</button>
            <button type="submit" disabled={mutation.isPending} className="btn-primary">
              {mutation.isPending ? 'Creating…' : 'Create Staff Member'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function RowActions({ row, onDeactivate, onActivate, onEdit }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    function handler(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  return (
    <div className="relative" ref={ref}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400"
      >
        <MoreVertical className="w-4 h-4" />
      </button>
      {open && (
        <div className="absolute right-0 top-6 z-30 bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-lg shadow-lg py-1 min-w-[140px]">
          <button
            className="w-full text-left px-4 py-2 text-xs text-gray-700 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700"
            onClick={() => { setOpen(false); onEdit(row); }}
          >
            Edit Role
          </button>
          {row.is_active ? (
            <button
              className="w-full text-left px-4 py-2 text-xs text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20"
              onClick={() => { setOpen(false); onDeactivate(row); }}
            >
              Deactivate
            </button>
          ) : (
            <button
              className="w-full text-left px-4 py-2 text-xs text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20"
              onClick={() => { setOpen(false); onActivate(row); }}
            >
              Reactivate
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function EditRoleModal({ staff, onClose, onSuccess }) {
  const [role, setRole] = useState(staff.role);
  const [error, setError] = useState('');

  const mutation = useMutation({
    mutationFn: () => staffApi.update(staff.id, { role }),
    onSuccess: () => { onSuccess(); onClose(); },
    onError: (e) => setError(e.data?.detail || e.message || 'Update failed.'),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-modal border border-gray-100 dark:border-gray-700 w-full max-w-sm mx-4 overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-700">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">
            Edit Role — {staff.full_name}
          </h2>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-400">
            <X className="w-4 h-4" />
          </button>
        </div>
        <div className="px-5 py-4 space-y-3">
          <select
            className="select"
            value={role}
            onChange={(e) => { setRole(e.target.value); setError(''); }}
          >
            <option value="support">Support</option>
            <option value="compliance_officer">Compliance Officer</option>
            <option value="super_admin">Super Admin</option>
          </select>
          {error && <p className="text-xs text-red-600 dark:text-red-400">{error}</p>}
          <div className="flex justify-end gap-2 pt-1">
            <button onClick={onClose} className="btn-ghost">Cancel</button>
            <button
              onClick={() => mutation.mutate()}
              disabled={mutation.isPending || role === staff.role}
              className="btn-primary"
            >
              {mutation.isPending ? 'Saving…' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function EmployeesPage() {
  const { user: me } = useAuth();
  const qc = useQueryClient();

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [ordering, setOrdering] = useState('-date_joined');
  const [roleFilter, setRoleFilter] = useState('');
  const [activeFilter, setActiveFilter] = useState('');
  const [showInvite, setShowInvite] = useState(false);
  const [editStaff, setEditStaff] = useState(null);

  const listParams = {
    page,
    page_size: pageSize,
    search: search || undefined,
    ordering,
    role: roleFilter || undefined,
    is_active: activeFilter || undefined,
  };

  const { data: listData, isLoading: listLoading, error: listError } = useQuery({
    queryKey: ['platform-staff', listParams],
    queryFn: () => staffApi.list(listParams),
    keepPreviousData: true,
  });

  const { data: statsData } = useQuery({
    queryKey: ['platform-staff-stats'],
    queryFn: staffApi.stats,
    staleTime: 30_000,
  });

  const invalidate = () => {
    qc.invalidateQueries({ queryKey: ['platform-staff'] });
    qc.invalidateQueries({ queryKey: ['platform-staff-stats'] });
  };

  const deactivateMutation = useMutation({
    mutationFn: (id) => staffApi.deactivate(id),
    onSuccess: invalidate,
  });

  const activateMutation = useMutation({
    mutationFn: (id) => staffApi.activate(id),
    onSuccess: invalidate,
  });

  const rows = listData?.results ?? [];
  const total = listData?.count ?? 0;

  function handleSearch(val) { setSearch(val); setPage(1); }
  function handleSort(field) {
    setOrdering((prev) => (prev === field ? `-${field}` : field));
    setPage(1);
  }

  const columns = [
    {
      key: 'full_name',
      label: 'Name',
      sortable: true,
      render: (row) => (
        <div>
          <p className="font-medium text-gray-900 dark:text-white text-xs">{row.full_name}</p>
          <p className="text-gray-400 dark:text-gray-500 text-xs">{row.email}</p>
        </div>
      ),
    },
    {
      key: 'role',
      label: 'Role',
      sortable: true,
      render: (row) => <RoleBadge role={row.role} />,
    },
    {
      key: 'is_active',
      label: 'Status',
      render: (row) => (
        <Badge
          status={row.is_active ? 'active' : 'suspended'}
          label={row.is_active ? 'Active' : 'Inactive'}
          showDot
        />
      ),
    },
    {
      key: 'mfa_enabled',
      label: 'MFA',
      render: (row) => (
        <span className={`text-xs font-medium ${row.mfa_enabled ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-400 dark:text-gray-500'}`}>
          {row.mfa_enabled ? 'Enabled' : 'Disabled'}
        </span>
      ),
    },
    {
      key: 'date_joined',
      label: 'Joined',
      sortable: true,
      render: (row) => (
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {row.date_joined ? new Date(row.date_joined).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—'}
        </span>
      ),
    },
    {
      key: '_actions',
      label: '',
      render: (row) => (
        <RowActions
          row={row}
          onDeactivate={(r) => {
            if (r.id === me?.id) return alert('You cannot deactivate your own account.');
            deactivateMutation.mutate(r.id);
          }}
          onActivate={(r) => activateMutation.mutate(r.id)}
          onEdit={(r) => setEditStaff(r)}
        />
      ),
    },
  ];

  const toolbar = (
    <div className="flex items-center gap-2 flex-wrap">
      <select
        className="input text-xs py-1.5 px-2.5 min-w-[110px]"
        value={roleFilter}
        onChange={(e) => { setRoleFilter(e.target.value); setPage(1); }}
      >
        <option value="">All Roles</option>
        <option value="super_admin">Super Admin</option>
        <option value="support">Support</option>
        <option value="compliance_officer">Compliance Officer</option>
      </select>
      <select
        className="input text-xs py-1.5 px-2.5 min-w-[100px]"
        value={activeFilter}
        onChange={(e) => { setActiveFilter(e.target.value); setPage(1); }}
      >
        <option value="">All Status</option>
        <option value="true">Active</option>
        <option value="false">Inactive</option>
      </select>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">ICF Staff</h1>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">Manage ICF internal platform team members</p>
        </div>
        <button onClick={() => setShowInvite(true)} className="btn-primary">
          <Plus className="w-4 h-4" />
          Add Staff Member
        </button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <StatCard label="Total Staff"  value={statsData?.total}         icon={Users}      lightCls="bg-blue-50 text-blue-600"    darkCls="dark:bg-blue-900/30 dark:text-blue-400" />
        <StatCard label="Active"       value={statsData?.active}        icon={UserCheck}  lightCls="bg-emerald-50 text-emerald-600" darkCls="dark:bg-emerald-900/30 dark:text-emerald-400" />
        <StatCard label="Inactive"     value={statsData?.inactive}      icon={UserX}      lightCls="bg-red-50 text-red-600"      darkCls="dark:bg-red-900/30 dark:text-red-400" />
        <StatCard label="Super Admins" value={statsData?.super_admins}  icon={ShieldCheck} lightCls="bg-violet-50 text-violet-600" darkCls="dark:bg-violet-900/30 dark:text-violet-400" />
        <StatCard label="Support Team" value={statsData?.support_count} icon={Headphones} lightCls="bg-amber-50 text-amber-600"  darkCls="dark:bg-amber-900/30 dark:text-amber-400" />
      </div>

      <DataTable
        columns={columns}
        data={rows}
        loading={listLoading}
        error={listError ? 'Failed to load staff members.' : null}
        emptyText="No staff members found."
        totalCount={total}
        page={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={(s) => { setPageSize(s); setPage(1); }}
        ordering={ordering}
        onSort={handleSort}
        search={search}
        onSearch={handleSearch}
        searchPlaceholder="Search by name or email…"
        toolbar={toolbar}
        rowKey={(r) => r.id}
      />

      {showInvite && (
        <InviteModal onClose={() => setShowInvite(false)} onSuccess={invalidate} />
      )}
      {editStaff && (
        <EditRoleModal staff={editStaff} onClose={() => setEditStaff(null)} onSuccess={invalidate} />
      )}
    </div>
  );
}
