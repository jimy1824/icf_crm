import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Building2, Mail, Phone, Globe, MapPin, FileText, Edit2, Check, X, Upload,
} from 'lucide-react';
import { getCompanySettings, updateCompanySettings, updateCompanyLogo, getCompanyUsage } from '../../api/company.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import { useAuth } from '../../hooks/useAuth.js';

function UsageBar({ label, current, limit }) {
  const pct = limit ? Math.min(100, Math.round((current / limit) * 100)) : 0;
  const color = pct >= 90 ? 'bg-red-500' : pct >= 70 ? 'bg-yellow-400' : 'bg-brand-500';
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-600 dark:text-gray-300 mb-1">
        <span>{label}</span>
        <span className="font-medium">{current.toLocaleString()} / {limit ? limit.toLocaleString() : '∞'}</span>
      </div>
      <div className="w-full h-2 rounded-full bg-gray-100 dark:bg-gray-700 overflow-hidden">
        <div className={`h-2 rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function InfoRow({ label, value }) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-gray-50 dark:border-gray-800 last:border-0">
      <span className="w-36 text-xs text-gray-400 flex-shrink-0">{label}</span>
      <span className="text-sm text-gray-900 dark:text-white">{value || <span className="text-gray-400 italic">Not set</span>}</span>
    </div>
  );
}

function EditableField({ label, name, value, type = 'text', onSave }) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(value ?? '');

  const handleSave = () => {
    onSave(name, draft);
    setEditing(false);
  };
  const handleCancel = () => {
    setDraft(value ?? '');
    setEditing(false);
  };

  if (editing) {
    return (
      <div className="flex items-start gap-3 py-3 border-b border-gray-50 dark:border-gray-800 last:border-0">
        <span className="w-36 text-xs text-gray-400 flex-shrink-0 pt-1">{label}</span>
        <div className="flex items-center gap-2 flex-1">
          <input
            type={type}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="input text-sm flex-1"
            autoFocus
          />
          <button onClick={handleSave} className="p-1.5 rounded-lg bg-brand-600 text-white hover:bg-brand-700">
            <Check className="w-3.5 h-3.5" />
          </button>
          <button onClick={handleCancel} className="p-1.5 rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800">
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      className="flex items-start gap-3 py-3 border-b border-gray-50 dark:border-gray-800 last:border-0 group cursor-pointer"
      onClick={() => setEditing(true)}
    >
      <span className="w-36 text-xs text-gray-400 flex-shrink-0">{label}</span>
      <span className="text-sm text-gray-900 dark:text-white flex-1">
        {value || <span className="text-gray-400 italic">Not set</span>}
      </span>
      <Edit2 className="w-3.5 h-3.5 text-gray-300 group-hover:text-brand-500 transition-colors flex-shrink-0 mt-0.5" />
    </div>
  );
}

export default function CompanyOverviewPage() {
  const { isFirmAdmin } = useAuth();
  const canEdit = isFirmAdmin();
  const qc = useQueryClient();

  const { data: company, isLoading } = useQuery({
    queryKey: ['company-settings'],
    queryFn: getCompanySettings,
  });

  const { data: usageData } = useQuery({
    queryKey: ['company-usage', company?.id],
    queryFn: () => getCompanyUsage(company.id),
    enabled: !!company?.id,
  });

  const updateMutation = useMutation({
    mutationFn: (data) => updateCompanySettings(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['company-settings'] }),
  });

  const logoMutation = useMutation({
    mutationFn: (logo_url) => updateCompanyLogo(logo_url),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['company-settings'] }),
  });

  const handleFieldSave = (field, value) => {
    updateMutation.mutate({ [field]: value });
  };

  const handleLogoUpdate = () => {
    const url = window.prompt('Enter logo URL (paste a direct image URL):');
    if (url && url.startsWith('http')) {
      logoMutation.mutate(url);
    }
  };

  if (isLoading) {
    return (
      <div>
        <PageHeader title="Company Overview" icon={Building2} />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mt-5">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card p-5">
              <div className="skeleton h-4 w-1/3 rounded mb-3" />
              <div className="space-y-3">
                {[1, 2, 3].map((j) => <div key={j} className="skeleton h-3 rounded w-full" />)}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  const sub = company?.subscription;
  const usage = usageData;

  return (
    <div>
      <PageHeader
        title="Company Overview"
        subtitle={company?.firm_name}
        icon={Building2}
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mt-5">
        {/* ── Logo + identity ── */}
        <div className="card p-5 flex flex-col gap-4">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 rounded-xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center overflow-hidden flex-shrink-0">
              {company?.logo_url
                ? <img src={company.logo_url} alt="Logo" className="w-full h-full object-contain" />
                : <Building2 className="w-8 h-8 text-gray-400" />}
            </div>
            <div className="min-w-0">
              <p className="font-semibold text-gray-900 dark:text-white text-sm truncate">{company?.firm_name}</p>
              <p className="text-xs text-gray-400">{company?.region || 'No region set'}</p>
              {canEdit && (
                <button
                  onClick={handleLogoUpdate}
                  className="mt-1.5 flex items-center gap-1 text-xs text-brand-600 hover:text-brand-700"
                >
                  <Upload className="w-3 h-3" />
                  Update logo
                </button>
              )}
            </div>
          </div>

          <div className="space-y-1 text-xs text-gray-500 dark:text-gray-400">
            <div className="flex items-center gap-2">
              <Mail className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="truncate">{company?.company_email || '—'}</span>
            </div>
            <div className="flex items-center gap-2">
              <Phone className="w-3.5 h-3.5 flex-shrink-0" />
              <span>{company?.phone || '—'}</span>
            </div>
            <div className="flex items-center gap-2">
              <Globe className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="truncate">{company?.website || '—'}</span>
            </div>
            <div className="flex items-center gap-2">
              <MapPin className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="truncate">
                {[company?.city, company?.state, company?.country].filter(Boolean).join(', ') || '—'}
              </span>
            </div>
          </div>
        </div>

        {/* ── Company details ── */}
        <div className="card p-5 lg:col-span-2">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Company Details</h3>
          {canEdit ? (
            <div>
              <EditableField label="Firm Name" name="firm_name" value={company?.firm_name} onSave={handleFieldSave} />
              <EditableField label="Legal Name" name="legal_name" value={company?.legal_name} onSave={handleFieldSave} />
              <EditableField label="Registration #" name="registration_number" value={company?.registration_number} onSave={handleFieldSave} />
              <EditableField label="Tax Number" name="tax_number" value={company?.tax_number} onSave={handleFieldSave} />
              <EditableField label="Company Email" name="company_email" value={company?.company_email} type="email" onSave={handleFieldSave} />
              <EditableField label="Phone" name="phone" value={company?.phone} onSave={handleFieldSave} />
              <EditableField label="Website" name="website" value={company?.website} type="url" onSave={handleFieldSave} />
              <EditableField label="Address" name="address_line1" value={company?.address_line1} onSave={handleFieldSave} />
              <EditableField label="City" name="city" value={company?.city} onSave={handleFieldSave} />
              <EditableField label="State" name="state" value={company?.state} onSave={handleFieldSave} />
              <EditableField label="Postal Code" name="postal_code" value={company?.postal_code} onSave={handleFieldSave} />
              <EditableField label="Country" name="country" value={company?.country} onSave={handleFieldSave} />
            </div>
          ) : (
            <div>
              <InfoRow label="Firm Name" value={company?.firm_name} />
              <InfoRow label="Legal Name" value={company?.legal_name} />
              <InfoRow label="Registration #" value={company?.registration_number} />
              <InfoRow label="Tax Number" value={company?.tax_number} />
              <InfoRow label="Company Email" value={company?.company_email} />
              <InfoRow label="Phone" value={company?.phone} />
              <InfoRow label="Website" value={company?.website} />
              <InfoRow label="Address" value={[company?.address_line1, company?.city, company?.state, company?.postal_code, company?.country].filter(Boolean).join(', ')} />
            </div>
          )}
        </div>

        {/* ── Subscription + usage ── */}
        {sub && (
          <div className="card p-5 lg:col-span-3">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Subscription &amp; Usage</h3>
              <div className="flex items-center gap-2">
                <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium
                  ${sub.status === 'active' ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                  : sub.status === 'trial' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                  : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'}`}
                >
                  {sub.is_trial ? 'Trial' : sub.status}
                </span>
                <span className="text-sm font-medium text-gray-900 dark:text-white">
                  {sub.plan?.name}
                </span>
              </div>
            </div>

            {sub.is_trial && sub.trial_expires_at && (
              <p className="text-xs text-yellow-600 dark:text-yellow-400 mb-4">
                Trial expires {new Date(sub.trial_expires_at).toLocaleDateString()}
              </p>
            )}

            {usage && (
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
                <UsageBar label="Leads" current={usage.leads?.current ?? 0} limit={usage.leads?.limit} />
                <UsageBar label="Users" current={usage.users?.current ?? 0} limit={usage.users?.limit} />
                <UsageBar label="Campaigns" current={usage.campaigns?.current ?? 0} limit={usage.campaigns?.limit} />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
