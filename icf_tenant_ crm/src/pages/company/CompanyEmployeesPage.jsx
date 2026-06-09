import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Users, Plus, UserX } from 'lucide-react';
import { getEmployees, createEmployee, deactivateEmployee } from '../../api/company.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import DataTable from '../../components/ui/DataTable.jsx';
import Badge from '../../components/ui/Badge.jsx';
import ConfirmModal from '../../components/ui/ConfirmModal.jsx';
import { useAuth } from '../../hooks/useAuth.js';

const ROLE_LABELS = {
  tenant_admin: 'Tenant Admin',
  team_lead: 'Team Lead',
  advisor: 'Advisor',
};

function CreateEmployeeModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    email: '', password: '', first_name: '', last_name: '',
    role_slug: 'advisor', job_title: '',
  });
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const handleChange = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    const errs = {};
    if (!form.email) errs.email = 'Required';
    if (!form.password || form.password.length < 8) errs.password = 'Min 8 characters';
    if (!form.first_name) errs.first_name = 'Required';
    if (!form.last_name) errs.last_name = 'Required';
    if (Object.keys(errs).length) { setErrors(errs); return; }
    setSaving(true);
    try {
      await createEmployee(form);
      onCreated();
    } catch (err) {
      const data = err.response?.data;
      if (typeof data === 'object') setErrors(data);
      else setErrors({ _: 'An error occurred. Please try again.' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-900 rounded-2xl shadow-xl w-full max-w-md p-6">
        <h2 className="text-base font-semibold text-gray-900 dark:text-white mb-4">Add Employee</h2>
        {errors._ && <p className="text-xs text-red-600 mb-3">{errors._}</p>}
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">First Name</label>
              <input name="first_name" value={form.first_name} onChange={handleChange} className="input" />
              {errors.first_name && <p className="text-xs text-red-600 mt-0.5">{errors.first_name}</p>}
            </div>
            <div>
              <label className="label">Last Name</label>
              <input name="last_name" value={form.last_name} onChange={handleChange} className="input" />
              {errors.last_name && <p className="text-xs text-red-600 mt-0.5">{errors.last_name}</p>}
            </div>
          </div>
          <div>
            <label className="label">Email</label>
            <input name="email" type="email" value={form.email} onChange={handleChange} className="input" />
            {errors.email && <p className="text-xs text-red-600 mt-0.5">{errors.email}</p>}
          </div>
          <div>
            <label className="label">Password</label>
            <input name="password" type="password" value={form.password} onChange={handleChange} className="input" />
            {errors.password && <p className="text-xs text-red-600 mt-0.5">{errors.password}</p>}
          </div>
          <div>
            <label className="label">Role</label>
            <select name="role_slug" value={form.role_slug} onChange={handleChange} className="input">
              <option value="advisor">Advisor</option>
              <option value="team_lead">Team Lead</option>
              <option value="tenant_admin">Tenant Admin</option>
            </select>
          </div>
          <div>
            <label className="label">Job Title <span className="text-gray-400">(optional)</span></label>
            <input name="job_title" value={form.job_title} onChange={handleChange} className="input" />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary btn-sm">Cancel</button>
            <button type="submit" className="btn-primary btn-sm" disabled={saving}>
              {saving ? 'Creating…' : 'Create Employee'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function CompanyEmployeesPage() {
  const { isFirmAdmin } = useAuth();
  const canManage = isFirmAdmin();
  const qc = useQueryClient();

  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [search, setSearch] = useState('');
  const [ordering, setOrdering] = useState('user__last_name');
  const [activeFilter, setActiveFilter] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [confirmDeactivate, setConfirmDeactivate] = useState(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['company-employees', page, pageSize, search, ordering, activeFilter],
    queryFn: () => getEmployees({
      page,
      page_size: pageSize,
      search: search || undefined,
      ordering,
      is_active: activeFilter !== '' ? activeFilter : undefined,
    }),
    keepPreviousData: true,
  });

  const deactivateMutation = useMutation({
    mutationFn: (id) => deactivateEmployee(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['company-employees'] });
      setConfirmDeactivate(null);
    },
  });

  const employees = data?.results ?? [];
  const total = data?.count ?? 0;

  const columns = [
    {
      key: 'full_name',
      label: 'Name',
      sortable: true,
      render: (row) => (
        <div>
          <p className="font-medium text-gray-900 dark:text-white text-xs">{row.full_name}</p>
          <p className="text-[10px] text-gray-400">{row.email}</p>
        </div>
      ),
    },
    {
      key: 'primary_role',
      label: 'Role',
      render: (row) => (
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300">
          {ROLE_LABELS[row.primary_role] ?? row.primary_role ?? '—'}
        </span>
      ),
    },
    {
      key: 'job_title',
      label: 'Title',
      render: (row) => <span className="text-xs text-gray-500">{row.job_title || '—'}</span>,
    },
    {
      key: 'is_active',
      label: 'Status',
      render: (row) => <Badge status={row.is_active ? 'active' : 'inactive'} showDot />,
    },
    {
      key: 'created_at',
      label: 'Joined',
      sortable: true,
      render: (row) => (
        <span className="text-xs text-gray-400">
          {row.created_at ? new Date(row.created_at).toLocaleDateString() : '—'}
        </span>
      ),
    },
    ...(canManage ? [{
      key: '_actions',
      label: '',
      render: (row) => (
        row.is_active ? (
          <button
            onClick={() => setConfirmDeactivate(row)}
            className="inline-flex items-center gap-1 text-[10px] text-red-600 hover:text-red-700 font-medium"
          >
            <UserX className="w-3 h-3" />
            Deactivate
          </button>
        ) : null
      ),
    }] : []),
  ];

  const toolbar = (
    <select
      value={activeFilter}
      onChange={(e) => { setActiveFilter(e.target.value); setPage(1); }}
      className="text-xs border border-gray-200 dark:border-gray-600 rounded-lg px-2 py-1.5 bg-white dark:bg-gray-800"
    >
      <option value="">All employees</option>
      <option value="true">Active only</option>
      <option value="false">Inactive only</option>
    </select>
  );

  return (
    <div>
      <PageHeader
        title="Employees"
        subtitle="Manage firm staff and their roles"
        icon={Users}
        actions={
          canManage && (
            <button onClick={() => setShowCreate(true)} className="btn-primary btn-sm">
              <Plus className="w-3.5 h-3.5" />
              Add Employee
            </button>
          )
        }
      />

      <div className="mt-5">
        <DataTable
          columns={columns}
          data={employees}
          loading={isLoading}
          error={error ? 'Failed to load employees.' : null}
          emptyText="No employees found."
          totalCount={total}
          page={page}
          pageSize={pageSize}
          onPageChange={setPage}
          onPageSizeChange={(s) => { setPageSize(s); setPage(1); }}
          ordering={ordering}
          onSort={(f) => { setOrdering(f); setPage(1); }}
          search={search}
          onSearch={(s) => { setSearch(s); setPage(1); }}
          searchPlaceholder="Search by name or email…"
          toolbar={toolbar}
          rowKey={(r) => r.id}
        />
      </div>

      {showCreate && (
        <CreateEmployeeModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            qc.invalidateQueries({ queryKey: ['company-employees'] });
          }}
        />
      )}

      {confirmDeactivate && (
        <ConfirmModal
          title="Deactivate Employee"
          message={`Are you sure you want to deactivate ${confirmDeactivate.full_name}? They will lose access immediately.`}
          confirmLabel="Deactivate"
          danger
          onConfirm={() => deactivateMutation.mutate(confirmDeactivate.id)}
          onCancel={() => setConfirmDeactivate(null)}
        />
      )}
    </div>
  );
}
