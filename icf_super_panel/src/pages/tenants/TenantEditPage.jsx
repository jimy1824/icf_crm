import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { tenantsApi } from '../../api/tenants.js';
import { useFetch } from '../../hooks/useFetch.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import { PageSpinner } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';

const FIELDS = [
  { key: 'firm_name',           label: 'Firm Name',         required: true },
  { key: 'legal_name',          label: 'Legal Name' },
  { key: 'company_email',       label: 'Email',             type: 'email' },
  { key: 'phone',               label: 'Phone' },
  { key: 'website',             label: 'Website',           type: 'url' },
  { key: 'address_line1',       label: 'Street' },
  { key: 'address_line2',       label: 'Street Line 2' },
  { key: 'city',                label: 'City' },
  { key: 'state',               label: 'State' },
  { key: 'country',             label: 'Country' },
  { key: 'postal_code',         label: 'Postal Code' },
  { key: 'subdomain',           label: 'Subdomain',         mono: true },
  { key: 'custom_domain',       label: 'Custom Domain',     mono: true },
  { key: 'registration_number', label: 'Registration #' },
  { key: 'tax_number',          label: 'Tax #' },
];

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

export default function TenantEditPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: tenant, loading } = useFetch(() => tenantsApi.get(id), [id]);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (tenant) {
      const initial = {};
      FIELDS.forEach(({ key }) => { initial[key] = tenant[key] ?? ''; });
      setForm(initial);
    }
  }, [tenant]);

  function set(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const payload = {};
      FIELDS.forEach(({ key }) => { if (form[key] !== '') payload[key] = form[key]; });
      await tenantsApi.update(id, payload);
      navigate(`/tenants/${id}`);
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <PageSpinner />;

  return (
    <div className="max-w-2xl">
      <PageHeader
        crumbs={[{ label: 'Tenants', to: '/tenants' }, { label: tenant?.firm_name, to: `/tenants/${id}` }, { label: 'Edit' }]}
        title="Edit Tenant Profile"
      />

      <ErrorAlert error={error} className="mb-5" />

      <form onSubmit={handleSubmit}>
        <div className="card p-6 mb-6">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-700 pb-3 mb-4">
            Firm Details
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {FIELDS.map(({ key, label, type, required, mono }) => (
              <Field key={key} label={label} required={required}>
                <input
                  type={type ?? 'text'}
                  className={`input ${mono ? 'font-mono' : ''}`}
                  value={form[key] ?? ''}
                  onChange={(e) => set(key, e.target.value)}
                  required={required}
                />
              </Field>
            ))}
          </div>
        </div>

        <div className="flex items-center justify-end gap-3">
          <button type="button" className="btn-ghost" onClick={() => navigate(`/tenants/${id}`)}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? <><Spinner size="sm" />Saving…</> : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  );
}
