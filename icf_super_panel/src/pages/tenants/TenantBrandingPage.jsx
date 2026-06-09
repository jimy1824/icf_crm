import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CheckCircle, Palette } from 'lucide-react';
import { tenantsApi } from '../../api/tenants.js';
import { useFetch } from '../../hooks/useFetch.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import { PageSpinner } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';

function Field({ label, hint, children }) {
  return (
    <div className="space-y-1.5">
      <label className="block text-xs font-semibold text-gray-600 dark:text-gray-400 uppercase tracking-wide">{label}</label>
      {hint && <p className="text-xs text-gray-400">{hint}</p>}
      {children}
    </div>
  );
}

export default function TenantBrandingPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: branding, loading, refetch } = useFetch(() => tenantsApi.getBranding(id), [id]);
  const [form, setForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (branding) setForm(branding);
  }, [branding]);

  function set(key, value) {
    setForm((f) => ({ ...f, [key]: value }));
    setSaved(false);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setSaving(true); setError(null); setSaved(false);
    try {
      await tenantsApi.updateBranding(id, {
        primary_color: form.primary_color,
        secondary_color: form.secondary_color,
        login_bg_url: form.login_bg_url,
        custom_smtp_host: form.custom_smtp_host,
        custom_smtp_port: form.custom_smtp_port,
        custom_smtp_user: form.custom_smtp_user,
        custom_sms_provider: form.custom_sms_provider,
      });
      setSaved(true);
      refetch();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <PageSpinner />;

  return (
    <div className="max-w-xl">
      <PageHeader
        crumbs={[
          { label: 'Tenants', to: '/tenants' },
          { label: 'Tenant', to: `/tenants/${id}` },
          { label: 'Branding' },
        ]}
        title="Branding & White-label"
        subtitle="Configure tenant-specific colours, login assets, and messaging."
      />

      {saved && (
        <div className="flex items-center gap-2 mb-5 px-4 py-3 rounded-xl bg-emerald-50 dark:bg-emerald-900/30 border border-emerald-100 dark:border-emerald-800 text-emerald-700 dark:text-emerald-400 text-sm">
          <CheckCircle className="w-4 h-4 flex-shrink-0" />
          Branding configuration saved successfully.
        </div>
      )}
      <ErrorAlert error={error} className="mb-5" />

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Colors */}
        <div className="card p-6 space-y-5">
          <div className="flex items-center gap-2 border-b border-gray-100 dark:border-gray-700 pb-3">
            <Palette className="w-4 h-4 text-brand-600" />
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Brand Colors</h2>
          </div>
          <div className="grid grid-cols-2 gap-5">
            <Field label="Primary color">
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={form.primary_color ?? '#1A56DB'}
                  onChange={(e) => set('primary_color', e.target.value)}
                  className="w-10 h-9 rounded-lg border border-gray-200 cursor-pointer p-0.5"
                />
                <input
                  type="text"
                  className="input font-mono flex-1"
                  value={form.primary_color ?? ''}
                  onChange={(e) => set('primary_color', e.target.value)}
                  maxLength={7}
                  placeholder="#1A56DB"
                />
              </div>
            </Field>
            <Field label="Secondary color">
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={form.secondary_color ?? '#6B7280'}
                  onChange={(e) => set('secondary_color', e.target.value)}
                  className="w-10 h-9 rounded-lg border border-gray-200 cursor-pointer p-0.5"
                />
                <input
                  type="text"
                  className="input font-mono flex-1"
                  value={form.secondary_color ?? ''}
                  onChange={(e) => set('secondary_color', e.target.value)}
                  maxLength={7}
                  placeholder="#6B7280"
                />
              </div>
            </Field>
          </div>
        </div>

        {/* Login Page */}
        <div className="card p-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-700 pb-3">Login Page</h2>
          <Field label="Background Image URL" hint="Hosted image displayed behind the login form.">
            <input
              type="url"
              className="input"
              placeholder="https://cdn.example.com/bg.jpg"
              value={form.login_bg_url ?? ''}
              onChange={(e) => set('login_bg_url', e.target.value)}
            />
          </Field>
        </div>

        {/* SMTP */}
        <div className="card p-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-700 pb-3">Custom SMTP</h2>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="sm:col-span-2">
              <Field label="SMTP Host">
                <input
                  className="input"
                  placeholder="smtp.example.com"
                  value={form.custom_smtp_host ?? ''}
                  onChange={(e) => set('custom_smtp_host', e.target.value)}
                />
              </Field>
            </div>
            <Field label="Port">
              <input
                type="number"
                className="input"
                value={form.custom_smtp_port ?? 587}
                onChange={(e) => set('custom_smtp_port', Number(e.target.value))}
              />
            </Field>
          </div>
          <Field label="SMTP User">
            <input
              className="input"
              placeholder="noreply@example.com"
              value={form.custom_smtp_user ?? ''}
              onChange={(e) => set('custom_smtp_user', e.target.value)}
            />
          </Field>
        </div>

        {/* SMS */}
        <div className="card p-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white border-b border-gray-100 dark:border-gray-700 pb-3">SMS Provider</h2>
          <Field label="Provider slug" hint="Leave blank to use platform default Twilio credentials.">
            <input
              className="input"
              placeholder="twilio"
              value={form.custom_sms_provider ?? ''}
              onChange={(e) => set('custom_sms_provider', e.target.value)}
            />
          </Field>
        </div>

        <div className="flex items-center justify-end gap-3">
          <button type="button" className="btn-ghost" onClick={() => navigate(`/tenants/${id}`)}>
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? <><Spinner size="sm" />Saving…</> : 'Save Branding'}
          </button>
        </div>
      </form>
    </div>
  );
}
