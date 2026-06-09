import { useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { leadsApi } from '../../api/leads.js';
import { usersApi } from '../../api/users.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';
import { PageSpinner } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';

function Field({ label, error, children }) {
  return (
    <div className="space-y-1.5">
      <label className="label">{label}</label>
      {children}
      {error && <p className="form-error">{error.message}</p>}
    </div>
  );
}

const SOURCES = ['website','referral','social','email','phone','other'];

export default function LeadEditPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();
  const { register, handleSubmit, reset, formState: { errors } } = useForm();

  const { data: lead, isLoading } = useQuery({
    queryKey: ['lead', id],
    queryFn: () => leadsApi.get(id),
  });
  const { data: advisors } = useQuery({
    queryKey: ['users', 'advisors'],
    queryFn: () => usersApi.list({ role: 'advisor' }),
  });

  useEffect(() => {
    if (lead) reset(lead);
  }, [lead, reset]);

  const update = useMutation({
    mutationFn: (data) => leadsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lead', id] });
      qc.invalidateQueries({ queryKey: ['leads'] });
      toast.success('Lead updated');
      navigate(`/leads/${id}`);
    },
    onError: (e) => toast.error(e.message),
  });

  if (isLoading) return <PageSpinner />;

  const advisorList = advisors?.results ?? advisors ?? [];

  return (
    <div className="max-w-2xl">
      <PageHeader
        crumbs={[{ label: 'Leads', to: '/leads' }, { label: `${lead?.first_name} ${lead?.last_name}`, to: `/leads/${id}` }, { label: 'Edit' }]}
        title="Edit Lead"
      />
      {update.error && <ErrorAlert error={update.error} className="mb-5" />}

      <form onSubmit={handleSubmit((d) => update.mutate(d))} className="space-y-5">
        <div className="card p-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-800 pb-3">
            Contact Details
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <Field label="First Name" error={errors.first_name}>
              <input className="input" {...register('first_name', { required: 'Required' })} />
            </Field>
            <Field label="Last Name" error={errors.last_name}>
              <input className="input" {...register('last_name', { required: 'Required' })} />
            </Field>
            <Field label="Email">
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
                {SOURCES.map((s) => <option key={s} value={s}>{s}</option>)}
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
        </div>

        <div className="flex justify-end gap-3">
          <button type="button" className="btn-outline" onClick={() => navigate(`/leads/${id}`)}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={update.isPending}>
            {update.isPending && <Spinner size="sm" />}
            Save Changes
          </button>
        </div>
      </form>
    </div>
  );
}
