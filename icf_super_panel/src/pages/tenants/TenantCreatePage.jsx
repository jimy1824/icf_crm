import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { tenantsApi, plansApi } from '../../api/tenants.js';
import { useFetch } from '../../hooks/useFetch.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';
import { PageSpinner } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';

function Field({ label, required, children }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">
        {label}{required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  );
}

export default function TenantCreatePage() {
  const navigate = useNavigate();
  const { data: plans, loading: plansLoading } = useFetch(() => plansApi.list());
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    firm_name: '', legal_name: '', company_email: '', phone: '', website: '',
    address_line1: '', city: '', state: '', country: 'US', postal_code: '',
    timezone: 'America/New_York', plan_id: '', is_trial: false, trial_days: 14,
  });

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const payload = { ...form, plan_id: Number(form.plan_id) };
      if (!payload.is_trial) delete payload.trial_days;
      const tenant = await tenantsApi.create(payload);
      navigate(`/tenants/${tenant.id}`);
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  if (plansLoading) return <PageSpinner />;

  return (
    <div className="max-w-2xl">
      <PageHeader
        crumbs={[{ label: 'Tenants', to: '/tenants' }, { label: 'New Tenant' }]}
        title="Provision New Tenant"
        subtitle="Creates a firm account and initial subscription on the platform."
      />

      <ErrorAlert error={error} className="mb-5" />

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Firm Details */}
        <div className="card p-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-700 pb-3">Firm Details</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <Field label="Firm Name" required>
              <input className="input" value={form.firm_name}
                onChange={(e) => set('firm_name', e.target.value)} required />
            </Field>
            <Field label="Legal Name">
              <input className="input" value={form.legal_name}
                onChange={(e) => set('legal_name', e.target.value)} />
            </Field>
            <Field label="Company Email">
              <input className="input" type="email" value={form.company_email}
                onChange={(e) => set('company_email', e.target.value)} />
            </Field>
            <Field label="Phone">
              <input className="input" value={form.phone}
                onChange={(e) => set('phone', e.target.value)} />
            </Field>
            <Field label="Website">
              <input className="input" type="url" placeholder="https://" value={form.website}
                onChange={(e) => set('website', e.target.value)} />
            </Field>
            <Field label="Timezone">
              <input className="input" value={form.timezone}
                onChange={(e) => set('timezone', e.target.value)} />
            </Field>
          </div>
        </div>

        {/* Address */}
        <div className="card p-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-700 pb-3">Address</h2>
          <Field label="Street">
            <input className="input" value={form.address_line1}
              onChange={(e) => set('address_line1', e.target.value)} />
          </Field>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="sm:col-span-2">
              <Field label="City">
                <input className="input" value={form.city}
                  onChange={(e) => set('city', e.target.value)} />
              </Field>
            </div>
            <Field label="State">
              <input className="input" value={form.state}
                onChange={(e) => set('state', e.target.value)} />
            </Field>
            <Field label="Postal Code">
              <input className="input" value={form.postal_code}
                onChange={(e) => set('postal_code', e.target.value)} />
            </Field>
          </div>
        </div>

        {/* Subscription */}
        <div className="card p-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-700 pb-3">Subscription</h2>
          <Field label="Plan" required>
            <select className="select" value={form.plan_id}
              onChange={(e) => set('plan_id', e.target.value)} required>
              <option value="">Select a plan…</option>
              {(plans ?? []).map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </Field>

          <label className="flex items-center gap-3 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={form.is_trial}
              onChange={(e) => set('is_trial', e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 text-brand-600 focus:ring-brand-500"
            />
            <span className="text-sm text-gray-700 dark:text-gray-300">Start as trial period</span>
          </label>

          {form.is_trial && (
            <Field label="Trial Days">
              <input
                className="input w-32"
                type="number"
                min={1}
                max={365}
                value={form.trial_days}
                onChange={(e) => set('trial_days', Number(e.target.value))}
              />
            </Field>
          )}
        </div>

        <div className="flex items-center justify-end gap-3">
          <button type="button" className="btn-ghost" onClick={() => navigate('/tenants')}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? <><Spinner size="sm" />Creating…</> : 'Create Tenant'}
          </button>
        </div>
      </form>
    </div>
  );
}
