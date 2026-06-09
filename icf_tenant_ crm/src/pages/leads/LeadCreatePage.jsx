import { useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { leadsApi } from '../../api/leads.js';
import { usersApi } from '../../api/users.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';
import Spinner from '../../components/ui/Spinner.jsx';

function Field({ label, error, children, required }) {
  return (
    <div className="space-y-1.5">
      <label className="label">{label}{required && <span className="text-danger-500 ml-0.5">*</span>}</label>
      {children}
      {error && <p className="form-error">{error.message}</p>}
    </div>
  );
}

const SOURCES = ['website','referral','social','email','phone','other'];

export default function LeadCreatePage() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { register, handleSubmit, formState: { errors } } = useForm();

  const { data: advisors } = useQuery({
    queryKey: ['users', 'advisors'],
    queryFn: () => usersApi.list({ role: 'advisor' }),
  });

  const create = useMutation({
    mutationFn: (data) => leadsApi.create(data),
    onSuccess: (lead) => {
      qc.invalidateQueries({ queryKey: ['leads'] });
      toast.success('Lead created');
      navigate(`/leads/${lead.id}`);
    },
    onError: (e) => toast.error(e.message),
  });

  const advisorList = advisors?.results ?? advisors ?? [];

  return (
    <div className="max-w-2xl">
      <PageHeader
        crumbs={[{ label: 'Leads', to: '/leads' }, { label: 'New Lead' }]}
        title="Create New Lead"
      />

      {create.error && <ErrorAlert error={create.error} className="mb-5" />}

      <form onSubmit={handleSubmit((d) => create.mutate(d))} className="space-y-5">
        <div className="card p-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-800 pb-3">
            Contact Details
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="First Name" required error={errors.first_name}>
              <input className="input" {...register('first_name', { required: 'Required' })} />
            </Field>
            <Field label="Last Name" required error={errors.last_name}>
              <input className="input" {...register('last_name', { required: 'Required' })} />
            </Field>
            <Field label="Email" error={errors.email}>
              <input type="email" className="input" {...register('email')} />
            </Field>
            <Field label="Phone">
              <input className="input" {...register('phone')} />
            </Field>
            <Field label="City">
              <input className="input" {...register('city')} />
            </Field>
            <Field label="State">
              <input className="input" {...register('state')} />
            </Field>
          </div>
        </div>

        <div className="card p-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-800 pb-3">
            Lead Info
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Source">
              <select className="select" {...register('source')}>
                <option value="">Select source…</option>
                {SOURCES.map((s) => <option key={s} value={s} className="capitalize">{s}</option>)}
              </select>
            </Field>
            <Field label="Assign to Advisor">
              <select className="select" {...register('assigned_advisor')}>
                <option value="">Unassigned</option>
                {advisorList.map((a) => (
                  <option key={a.id} value={a.id}>{a.first_name} {a.last_name}</option>
                ))}
              </select>
            </Field>
          </div>
          <Field label="Notes">
            <textarea className="textarea" rows={3} {...register('notes')}
              placeholder="Initial notes about this lead…" />
          </Field>
        </div>

        <div className="flex justify-end gap-3">
          <button type="button" className="btn-outline" onClick={() => navigate('/leads')}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={create.isPending}>
            {create.isPending && <Spinner size="sm" />}
            Create Lead
          </button>
        </div>
      </form>
    </div>
  );
}
