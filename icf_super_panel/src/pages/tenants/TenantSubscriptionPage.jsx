import { useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { CreditCard, RefreshCw } from 'lucide-react';
import { tenantsApi, plansApi, subscriptionsApi } from '../../api/tenants.js';
import { useFetch } from '../../hooks/useFetch.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import Badge from '../../components/ui/Badge.jsx';
import { PageSpinner } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import ErrorAlert from '../../components/ui/ErrorAlert.jsx';

function InfoRow({ label, value, children }) {
  return (
    <div className="flex justify-between items-center py-2.5 border-b border-gray-50 dark:border-gray-700/50 last:border-0">
      <span className="text-xs text-gray-400">{label}</span>
      {children ?? <span className="text-xs text-gray-800 dark:text-gray-200">{value ?? '—'}</span>}
    </div>
  );
}

export default function TenantSubscriptionPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { data: tenant, loading, refetch } = useFetch(() => tenantsApi.get(id), [id]);
  const { data: plans } = useFetch(() => plansApi.list());
  const [selectedPlan, setSelectedPlan] = useState('');
  const [trialDays, setTrialDays] = useState(14);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  async function assignPlan() {
    if (!selectedPlan) return;
    setSaving(true); setError(null);
    try {
      await subscriptionsApi.assignPlan(tenant.subscription.id, Number(selectedPlan));
      refetch();
      setSelectedPlan('');
    } catch (err) { setError(err); }
    finally { setSaving(false); }
  }

  async function startTrial() {
    setSaving(true); setError(null);
    try {
      await subscriptionsApi.startTrial(
        tenant.subscription.id,
        selectedPlan ? Number(selectedPlan) : undefined,
        trialDays,
      );
      refetch();
    } catch (err) { setError(err); }
    finally { setSaving(false); }
  }

  if (loading) return <PageSpinner />;
  const sub = tenant?.subscription;

  return (
    <div className="max-w-xl">
      <PageHeader
        crumbs={[
          { label: 'Tenants', to: '/tenants' },
          { label: tenant?.firm_name, to: `/tenants/${id}` },
          { label: 'Subscription' },
        ]}
        title="Subscription Management"
        subtitle={tenant?.firm_name}
      />

      <ErrorAlert error={error} className="mb-5" />

      {/* Current subscription */}
      <div className="card p-6 mb-5">
        <div className="flex items-center gap-2 mb-4">
          <CreditCard className="w-4 h-4 text-brand-600" />
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Current Subscription</h2>
        </div>
        {sub ? (
          <div className="divide-y divide-gray-50 dark:divide-gray-700/50">
            <InfoRow label="Plan" value={sub.plan?.name} />
            <InfoRow label="Status"><Badge status={sub.status} showDot /></InfoRow>
            <InfoRow label="Billing cycle" value={sub.billing_cycle} />
            <InfoRow label="Trial" value={sub.is_trial ? `Yes — expires ${sub.trial_expires_at}` : 'No'} />
            <InfoRow label="Max leads" value={sub.plan?.max_leads === 0 ? '∞' : sub.plan?.max_leads} />
            <InfoRow label="Max users" value={sub.plan?.max_users === 0 ? '∞' : sub.plan?.max_users} />
            <InfoRow label="Max campaigns" value={sub.plan?.max_campaigns === 0 ? '∞' : sub.plan?.max_campaigns} />
          </div>
        ) : (
          <p className="text-sm text-gray-400">No active subscription.</p>
        )}
      </div>

      {/* Change plan */}
      <div className="card p-6 mb-5">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Change Plan</h2>
        <div className="flex items-center gap-3">
          <select
            className="select flex-1"
            value={selectedPlan}
            onChange={(e) => setSelectedPlan(e.target.value)}
          >
            <option value="">Select new plan…</option>
            {(plans ?? []).map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <button
            className="btn-primary whitespace-nowrap"
            disabled={!selectedPlan || saving}
            onClick={assignPlan}
          >
            {saving ? <Spinner size="sm" /> : <RefreshCw className="w-3.5 h-3.5" />}
            Assign Plan
          </button>
        </div>
      </div>

      {/* Trial management */}
      <div className="card p-6">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-4">Trial Management</h2>
        <div className="flex items-center gap-3">
          <div className="space-y-1 flex-shrink-0">
            <label className="block text-xs text-gray-500 dark:text-gray-400">Trial days</label>
            <input
              type="number"
              min={1}
              max={365}
              value={trialDays}
              onChange={(e) => setTrialDays(Number(e.target.value))}
              className="input w-24 text-center"
            />
          </div>
          <div className="space-y-1 flex-1">
            <label className="block text-xs text-gray-500 dark:text-gray-400">Optional plan override</label>
            <select className="select" value={selectedPlan} onChange={(e) => setSelectedPlan(e.target.value)}>
              <option value="">Current plan</option>
              {(plans ?? []).map((p) => (
                <option key={p.id} value={p.id}>{p.name}</option>
              ))}
            </select>
          </div>
          <button
            className="btn-ghost border border-gray-200 dark:border-gray-600 mt-5 whitespace-nowrap"
            disabled={saving}
            onClick={startTrial}
          >
            {sub?.is_trial ? 'Extend Trial' : 'Start Trial'}
          </button>
        </div>
      </div>
    </div>
  );
}
