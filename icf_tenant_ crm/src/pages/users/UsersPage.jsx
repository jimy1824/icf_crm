import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import toast from 'react-hot-toast';
import { Plus, Search, Shield, Users } from 'lucide-react';
import { usersApi } from '../../api/users.js';
import { useDebounce } from '../../hooks/useDebounce.js';
import { useAuth } from '../../hooks/useAuth.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { SkeletonRow } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import ConfirmModal from '../../components/ui/ConfirmModal.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';

const ROLES = ['advisor', 'senior_advisor', 'team_lead', 'firm_admin'];

export default function UsersPage() {
  const { isFirmAdmin } = useAuth();
  const qc = useQueryClient();
  const [search, setSearch] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [confirm, setConfirm] = useState(null);
  const dq = useDebounce(search, 350);

  const { data, isLoading } = useQuery({
    queryKey: ['users', dq],
    queryFn: () => usersApi.list(dq ? { search: dq } : {}),
  });

  const { register, handleSubmit, reset, formState: { errors } } = useForm();

  const createUser = useMutation({
    mutationFn: (data) => usersApi.create(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] });
      toast.success('User invited');
      reset();
      setShowCreate(false);
    },
    onError: (e) => toast.error(e.message),
  });

  const deactivate = useMutation({
    mutationFn: (userId) => usersApi.deactivate(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] });
      toast.success('User deactivated');
      setConfirm(null);
    },
    onError: (e) => toast.error(e.message),
  });

  if (!isFirmAdmin()) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <Shield className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <p className="text-sm text-gray-500">Only Firm Admins can manage users.</p>
        </div>
      </div>
    );
  }

  const users = data?.results ?? data ?? [];

  return (
    <div>
      {confirm && <ConfirmModal {...confirm} onCancel={() => setConfirm(null)} />}

      <PageHeader
        title="Team Members"
        subtitle="Manage advisors and roles within your firm"
        icon={Users}
        actions={
          <button onClick={() => setShowCreate(!showCreate)} className="btn-primary btn-sm">
            <Plus className="w-3.5 h-3.5" />
            Invite User
          </button>
        }
      />

      {showCreate && (
        <div className="card p-5 mb-5">
          <h3 className="section-title mb-4">Invite Team Member</h3>
          <form onSubmit={handleSubmit((d) => createUser.mutate(d))} className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <div className="space-y-1.5">
              <label className="label">First Name</label>
              <input className="input" {...register('first_name', { required: 'Required' })} />
              {errors.first_name && <p className="form-error">{errors.first_name.message}</p>}
            </div>
            <div className="space-y-1.5">
              <label className="label">Last Name</label>
              <input className="input" {...register('last_name', { required: 'Required' })} />
              {errors.last_name && <p className="form-error">{errors.last_name.message}</p>}
            </div>
            <div className="space-y-1.5">
              <label className="label">Email</label>
              <input type="email" className="input" {...register('email', { required: 'Required' })} />
              {errors.email && <p className="form-error">{errors.email.message}</p>}
            </div>
            <div className="space-y-1.5">
              <label className="label">Role</label>
              <select className="select" {...register('role', { required: true })}>
                {ROLES.map((r) => <option key={r} value={r}>{r.replace(/_/g, ' ')}</option>)}
              </select>
            </div>
            <div className="col-span-full flex justify-end gap-2">
              <button type="button" className="btn-outline btn-sm" onClick={() => setShowCreate(false)}>Cancel</button>
              <button type="submit" className="btn-primary btn-sm" disabled={createUser.isPending}>
                {createUser.isPending && <Spinner size="sm" />}
                Send Invite
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="relative max-w-sm mb-5">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input className="input pl-10" placeholder="Search team members…"
          value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      <div className="card overflow-hidden">
        <table className="w-full">
          <thead><tr>
            <th className="th">Name</th>
            <th className="th hidden md:table-cell">Email</th>
            <th className="th">Role</th>
            <th className="th hidden lg:table-cell">Clients</th>
            <th className="th">Status</th>
            <th className="th">Actions</th>
          </tr></thead>
          <tbody>
            {isLoading && [1,2,3].map((i) => <SkeletonRow key={i} cols={6} />)}
            {!isLoading && users.map((u) => (
              <tr key={u.id} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/60">
                <td className="td">
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-full bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center flex-shrink-0">
                      <span className="text-xs font-bold text-brand-600">
                        {(u.first_name?.[0] ?? '') + (u.last_name?.[0] ?? '')}
                      </span>
                    </div>
                    <p className="text-sm font-medium text-gray-800 dark:text-gray-200">{u.first_name} {u.last_name}</p>
                  </div>
                </td>
                <td className="td hidden md:table-cell text-xs text-gray-500">{u.email}</td>
                <td className="td">
                  <span className="text-xs capitalize text-gray-700 dark:text-gray-300">{u.role?.replace(/_/g,' ')}</span>
                </td>
                <td className="td hidden lg:table-cell text-xs text-gray-500">{u.client_count ?? '—'}</td>
                <td className="td"><Badge status={u.is_active ? 'active' : 'inactive'} showDot /></td>
                <td className="td">
                  {u.is_active && (
                    <button
                      onClick={() => setConfirm({
                        title: 'Deactivate User',
                        message: `Deactivate ${u.first_name} ${u.last_name}? They will lose access immediately.`,
                        danger: true,
                        onConfirm: () => deactivate.mutate(u.id),
                        loading: deactivate.isPending,
                      })}
                      className="text-xs text-danger-600 hover:text-danger-700 font-medium">
                      Deactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {!isLoading && users.length === 0 && (
              <tr><td colSpan={6} className="td py-0">
                <EmptyState icon={Users} title="No team members found" subtitle="Invite your first advisor." />
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
