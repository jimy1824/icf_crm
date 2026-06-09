import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Palette, Save, Eye } from 'lucide-react';
import { getCompanySettings, getCompanyBranding, updateCompanyBranding } from '../../api/company.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import { useAuth } from '../../hooks/useAuth.js';

function ColorSwatch({ color, label, name, value, onChange, disabled }) {
  return (
    <div>
      <label className="label">{label}</label>
      <div className="flex items-center gap-2">
        <div
          className="w-9 h-9 rounded-lg border border-gray-200 dark:border-gray-600 flex-shrink-0 cursor-pointer"
          style={{ backgroundColor: value || '#ccc' }}
          onClick={() => !disabled && document.getElementById(`color-${name}`)?.click()}
        />
        <input
          id={`color-${name}`}
          type="color"
          value={value || '#000000'}
          onChange={(e) => onChange(name, e.target.value)}
          disabled={disabled}
          className="sr-only"
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(name, e.target.value)}
          disabled={disabled}
          maxLength={7}
          pattern="^#[0-9a-fA-F]{6}$"
          placeholder="#1A56DB"
          className="input font-mono text-sm flex-1"
        />
      </div>
    </div>
  );
}

export default function CompanyBrandingPage() {
  const { isFirmAdmin } = useAuth();
  const canEdit = isFirmAdmin();
  const qc = useQueryClient();

  const { data: company } = useQuery({
    queryKey: ['company-settings'],
    queryFn: getCompanySettings,
  });

  const { data: branding, isLoading } = useQuery({
    queryKey: ['company-branding', company?.id],
    queryFn: () => getCompanyBranding(company.id),
    enabled: !!company?.id,
  });

  const [form, setForm] = useState({
    primary_color: '#1A56DB',
    secondary_color: '#6B7280',
    login_bg_url: '',
    custom_smtp_host: '',
    custom_smtp_port: 587,
    custom_smtp_user: '',
    custom_sms_provider: '',
  });
  const [dirty, setDirty] = useState(false);
  const [saveStatus, setSaveStatus] = useState('');

  useEffect(() => {
    if (branding) {
      setForm({
        primary_color: branding.primary_color ?? '#1A56DB',
        secondary_color: branding.secondary_color ?? '#6B7280',
        login_bg_url: branding.login_bg_url ?? '',
        custom_smtp_host: branding.custom_smtp_host ?? '',
        custom_smtp_port: branding.custom_smtp_port ?? 587,
        custom_smtp_user: branding.custom_smtp_user ?? '',
        custom_sms_provider: branding.custom_sms_provider ?? '',
      });
      setDirty(false);
    }
  }, [branding]);

  const saveMutation = useMutation({
    mutationFn: (data) => updateCompanyBranding(company.id, data),
    onMutate: () => setSaveStatus('saving'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['company-branding'] });
      setDirty(false);
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus(''), 2000);
    },
    onError: () => setSaveStatus(''),
  });

  const handleChange = (name, value) => {
    setForm((f) => ({ ...f, [name]: value }));
    setDirty(true);
  };

  const handleInputChange = (e) => {
    handleChange(e.target.name, e.target.type === 'number' ? Number(e.target.value) : e.target.value);
  };

  return (
    <div>
      <PageHeader
        title="Theme &amp; Branding"
        subtitle="Customise colours, login page, and email settings"
        icon={Palette}
        actions={
          canEdit && dirty && (
            <button
              onClick={() => saveMutation.mutate(form)}
              disabled={saveMutation.isPending}
              className="btn-primary btn-sm"
            >
              <Save className="w-3.5 h-3.5" />
              {saveMutation.isPending ? 'Saving…' : 'Save Changes'}
            </button>
          )
        }
      />

      {saveStatus === 'saved' && (
        <div className="mt-4 p-3 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded-xl text-sm">
          Branding saved.
        </div>
      )}

      {isLoading ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mt-5">
          {[1, 2].map((i) => (
            <div key={i} className="card p-5">
              <div className="skeleton h-4 w-1/3 rounded mb-4" />
              <div className="space-y-3">
                {[1, 2, 3].map((j) => <div key={j} className="skeleton h-9 rounded-lg w-full" />)}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mt-5">
          {/* Colors */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Brand Colours</h3>
            <div className="space-y-4">
              <ColorSwatch
                label="Primary Colour"
                name="primary_color"
                value={form.primary_color}
                onChange={handleChange}
                disabled={!canEdit}
              />
              <ColorSwatch
                label="Secondary Colour"
                name="secondary_color"
                value={form.secondary_color}
                onChange={handleChange}
                disabled={!canEdit}
              />
            </div>

            {/* Preview */}
            <div className="mt-5 p-4 rounded-xl border border-gray-100 dark:border-gray-700">
              <p className="text-xs text-gray-400 mb-3 flex items-center gap-1">
                <Eye className="w-3.5 h-3.5" />
                Preview
              </p>
              <div className="flex items-center gap-2 flex-wrap">
                <button
                  style={{ backgroundColor: form.primary_color }}
                  className="px-4 py-2 rounded-xl text-white text-xs font-medium"
                >
                  Primary Button
                </button>
                <button
                  style={{ backgroundColor: form.secondary_color }}
                  className="px-4 py-2 rounded-xl text-white text-xs font-medium"
                >
                  Secondary
                </button>
                <span
                  style={{ color: form.primary_color }}
                  className="text-xs font-medium underline"
                >
                  Link text
                </span>
              </div>
            </div>
          </div>

          {/* Login background */}
          <div className="card p-5">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Login Page</h3>
            <div>
              <label className="label">Background Image URL</label>
              <input
                name="login_bg_url"
                value={form.login_bg_url}
                onChange={handleInputChange}
                disabled={!canEdit}
                placeholder="https://…"
                className="input"
              />
              <p className="text-xs text-gray-400 mt-1">Used as the login page background image.</p>
            </div>
            {form.login_bg_url && (
              <div className="mt-3 h-32 rounded-xl overflow-hidden border border-gray-100 dark:border-gray-700">
                <img src={form.login_bg_url} alt="Login BG" className="w-full h-full object-cover" onError={(e) => { e.target.style.display = 'none'; }} />
              </div>
            )}
          </div>

          {/* Email / SMTP */}
          <div className="card p-5 lg:col-span-2">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Custom Email (SMTP)</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="label">SMTP Host</label>
                <input
                  name="custom_smtp_host"
                  value={form.custom_smtp_host}
                  onChange={handleInputChange}
                  disabled={!canEdit}
                  placeholder="smtp.yourfirm.com"
                  className="input"
                />
              </div>
              <div>
                <label className="label">SMTP Port</label>
                <input
                  name="custom_smtp_port"
                  type="number"
                  value={form.custom_smtp_port}
                  onChange={handleInputChange}
                  disabled={!canEdit}
                  min={1}
                  max={65535}
                  className="input"
                />
              </div>
              <div>
                <label className="label">SMTP User</label>
                <input
                  name="custom_smtp_user"
                  value={form.custom_smtp_user}
                  onChange={handleInputChange}
                  disabled={!canEdit}
                  placeholder="noreply@yourfirm.com"
                  className="input"
                />
              </div>
              <div>
                <label className="label">SMS Provider <span className="text-gray-400">(optional)</span></label>
                <input
                  name="custom_sms_provider"
                  value={form.custom_sms_provider}
                  onChange={handleInputChange}
                  disabled={!canEdit}
                  placeholder="twilio / custom"
                  className="input"
                />
              </div>
            </div>
            {!canEdit && (
              <p className="mt-3 text-xs text-gray-400">Only Tenant Admin can modify branding settings.</p>
            )}
          </div>
        </div>
      )}

      {canEdit && dirty && (
        <div className="mt-4 flex justify-end">
          <button
            onClick={() => saveMutation.mutate(form)}
            disabled={saveMutation.isPending}
            className="btn-primary"
          >
            <Save className="w-4 h-4 mr-1.5" />
            {saveMutation.isPending ? 'Saving…' : 'Save Branding'}
          </button>
        </div>
      )}
    </div>
  );
}
