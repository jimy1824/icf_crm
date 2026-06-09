import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  AlertTriangle, ArrowLeft, Building2, CreditCard, Globe,
  Lock, Mail, MapPin, Palette, Phone, Unlock,
} from 'lucide-react';
import { tenantsApi } from '../../api/tenants.js';
import { useFetch } from '../../hooks/useFetch.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { PageSpinner } from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';
import ConfirmModal from '../../components/ui/ConfirmModal.jsx';

function InfoRow({ label, value, mono }) {
  return (
    <div className="flex justify-between items-start py-2.5 border-b border-gray-50 dark:border-gray-700/50 last:border-0">
      <span className="text-xs text-gray-400 w-32 flex-shrink-0">{label}</span>
      <span className={`text-xs text-right text-gray-800 dark:text-gray-200 ${mono ? 'font-mono' : ''}`}>{value || '—'}</span>
    </div>
  );
}

function UsageBar({ label, current, limit }) {
  const pct = limit === 0 ? 0 : Math.min(Math.round((current / limit) * 100), 100);
  const color = pct >= 90 ? 'bg-red-400' : pct >= 70 ? 'bg-amber-400' : 'bg-brand-500';
  return (
    <div className="space-y-1.5">
      <div className="flex justify-between text-xs text-gray-600 dark:text-gray-300">
        <span>{label}</span>
        <span className="font-medium">{current} / {limit === 0 ? '∞' : limit}</span>
      </div>
      {limit > 0 && (
        <div className="h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  );
}

export default function TenantDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: tenant, loading, error, refetch } = useFetch(() => tenantsApi.get(id), [id]);
  const { data: usage } = useFetch(() => tenantsApi.usage(id), [id]);

  const [confirm, setConfirm] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [trialDays, setTrialDays] = useState(14);

  async function doAction(action) {
    setActionError(null);
    try {
      await action();
      refetch();
    } catch (err) {
      setActionError(err);
    }
    setConfirm(null);
  }

  if (loading) return <PageSpinner />;
  if (error) return <ErrorAlert error={error} />;
  if (!tenant) return null;

  const sub = tenant.subscription;
  const addr = [tenant.address_line1, tenant.city, tenant.state, tenant.postal_code, tenant.country]
    .filter(Boolean).join(', ');

  return (
    <div>
      {confirm && (
        <ConfirmModal
          title={confirm.title}
          message={confirm.message}
          danger={confirm.danger}
          onConfirm={confirm.onConfirm}
          onCancel={() => setConfirm(null)}
        />
      )}

      <PageHeader
        crumbs={[{ label: 'Tenants', to: '/tenants' }, { label: tenant.firm_name }]}
        title={tenant.firm_name}
        subtitle={tenant.company_email || tenant.legal_name || ''}
        actions={
          <div className="flex items-center gap-2">
            <Link to={`/tenants/${id}/edit`} className="btn-ghost">Edit Profile</Link>
            {tenant.login_disabled ? (
              <button
                className="btn-ghost border border-gray-200 text-emerald-600"
                onClick={() => doAction(() => tenantsApi.enableLogin(id))}
              >
                <Unlock className="w-3.5 h-3.5" />
                Enable Login
              </button>
            ) : (
              <button
                className="btn-ghost border border-amber-200 text-amber-600"
                onClick={() => setConfirm({
                  title: 'Disable Login',
                  message: `This will lock out all users of "${tenant.firm_name}" immediately.`,
                  danger: true,
                  onConfirm: () => doAction(() => tenantsApi.disableLogin(id)),
                })}
              >
                <Lock className="w-3.5 h-3.5" />
                Disable Login
              </button>
            )}
            {tenant.status === 'active' ? (
              <button
                className="btn-primary bg-red-600 hover:bg-red-700"
                onClick={() => setConfirm({
                  title: 'Suspend Tenant',
                  message: `Suspend "${tenant.firm_name}"? Automation will halt and users locked out.`,
                  danger: true,
                  onConfirm: () => doAction(() => tenantsApi.suspend(id)),
                })}
              >
                <AlertTriangle className="w-3.5 h-3.5" />
                Suspend
              </button>
            ) : (
              <button
                className="btn-primary"
                onClick={() => doAction(() => tenantsApi.activate(id))}
              >
                Activate
              </button>
            )}
          </div>
        }
      />

      {actionError && <ErrorAlert error={actionError} className="mb-4" />}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Company info */}
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <Building2 className="w-4 h-4 text-brand-600" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Company</h3>
          </div>
          <div className="divide-y divide-gray-50 dark:divide-gray-700/50">
            <InfoRow label="Legal name" value={tenant.legal_name} />
            <InfoRow label="Email" value={tenant.company_email} />
            <InfoRow label="Phone" value={tenant.phone} />
            <InfoRow label="Website" value={tenant.website} />
            <InfoRow label="Address" value={addr} />
            <InfoRow label="Timezone" value={tenant.timezone} />
            <InfoRow label="Reg. number" value={tenant.registration_number} />
            <InfoRow label="Tax number" value={tenant.tax_number} />
            <div className="flex justify-between items-center py-2.5">
              <span className="text-xs text-gray-400">Status</span>
              <Badge status={tenant.status} showDot />
            </div>
            <div className="flex justify-between items-center py-2.5">
              <span className="text-xs text-gray-400">Login</span>
              <span className={`text-xs font-medium ${tenant.login_disabled ? 'text-red-600' : 'text-emerald-600'}`}>
                {tenant.login_disabled ? 'Disabled' : 'Enabled'}
              </span>
            </div>
          </div>
        </div>

        {/* Subscription */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <CreditCard className="w-4 h-4 text-brand-600" />
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Subscription</h3>
            </div>
            <Link to={`/tenants/${id}/subscription`} className="text-xs text-brand-600 font-medium">
              Manage →
            </Link>
          </div>

          {sub ? (
            <div className="space-y-0">
              <InfoRow label="Plan" value={sub.plan?.name} />
              <div className="flex justify-between items-center py-2.5 border-b border-gray-50 dark:border-gray-700/50">
                <span className="text-xs text-gray-400">Status</span>
                <Badge status={sub.status} showDot />
              </div>
              <InfoRow label="Billing" value={sub.billing_cycle} />
              <InfoRow label="Trial" value={sub.is_trial ? `Yes — expires ${sub.trial_expires_at}` : 'No'} />
              {sub.grace_period_ends_at && (
                <div className="flex justify-between items-center py-2.5 border-b border-gray-50 dark:border-gray-700/50">
                  <span className="text-xs text-red-500">Grace ends</span>
                  <span className="text-xs text-red-600 font-medium">{sub.grace_period_ends_at}</span>
                </div>
              )}
              {sub.ends_at && <InfoRow label="Renews" value={sub.ends_at} />}
            </div>
          ) : (
            <p className="text-sm text-gray-400">No subscription.</p>
          )}

          {sub?.is_trial && (
            <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-700 flex items-center gap-2">
              <input
                type="number"
                min={1}
                max={365}
                value={trialDays}
                onChange={(e) => setTrialDays(Number(e.target.value))}
                className="input w-20 text-center text-sm"
              />
              <button
                className="btn-ghost border border-gray-200 dark:border-gray-600 text-xs flex-1"
                onClick={() => doAction(() => tenantsApi.extendTrial(id, trialDays))}
              >
                Extend Trial
              </button>
            </div>
          )}
        </div>

        {/* Usage + Domain */}
        <div className="space-y-5">
          {usage && (
            <div className="card p-5">
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Usage</h3>
              <div className="space-y-3">
                {usage.leads && <UsageBar label="Leads" current={usage.leads.current} limit={usage.leads.limit} />}
                {usage.users && <UsageBar label="Users" current={usage.users.current} limit={usage.users.limit} />}
                {usage.campaigns && <UsageBar label="Campaigns" current={usage.campaigns.current} limit={usage.campaigns.limit} />}
              </div>
            </div>
          )}

          <div className="card p-5">
            <div className="flex items-center gap-2 mb-4">
              <Globe className="w-4 h-4 text-brand-600" />
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Domain</h3>
            </div>
            <div className="divide-y divide-gray-50 dark:divide-gray-700/50">
              <InfoRow label="Subdomain" value={tenant.subdomain} mono />
              <InfoRow label="Custom domain" value={tenant.custom_domain} mono />
              <div className="flex justify-between items-center py-2.5">
                <span className="text-xs text-gray-400">Domain status</span>
                <Badge status={tenant.domain_status || 'pending'} />
              </div>
            </div>
            <Link to={`/tenants/${id}/branding`} className="btn-ghost mt-3 w-full justify-center text-xs border border-gray-200 dark:border-gray-600">
              <Palette className="w-3.5 h-3.5" />
              Branding Config
            </Link>
          </div>
        </div>
      </div>

      <div className="mt-5 flex items-center gap-3">
        <Link to={`/billing?tenant_id=${id}`} className="btn-ghost border border-gray-200 dark:border-gray-600">
          <CreditCard className="w-4 h-4" />
          View Invoices
        </Link>
      </div>
    </div>
  );
}
