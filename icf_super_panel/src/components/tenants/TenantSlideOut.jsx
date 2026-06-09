import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Building2, CreditCard, ExternalLink, Globe, Mail, MapPin, Phone, X } from 'lucide-react';
import { tenantsApi } from '../../api/tenants.js';
import Badge from '../ui/Badge.jsx';
import { PageSpinner } from '../ui/Spinner.jsx';
import ErrorAlert from '../ui/ErrorAlert.jsx';

function Info({ icon: Icon, label, value }) {
  if (!value) return null;
  return (
    <div className="flex items-start gap-3">
      <Icon className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
      <div>
        <p className="text-xs text-gray-400">{label}</p>
        <p className="text-sm text-gray-900 dark:text-white mt-0.5">{value}</p>
      </div>
    </div>
  );
}

export default function TenantSlideOut({ tenantId, onClose }) {
  const [tenant, setTenant] = useState(null);
  const [usage, setUsage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!tenantId) return;
    setLoading(true); setError(null);
    Promise.all([tenantsApi.get(tenantId), tenantsApi.usage(tenantId)])
      .then(([t, u]) => { setTenant(t); setUsage(u); })
      .catch(setError)
      .finally(() => setLoading(false));
  }, [tenantId]);

  const sub = tenant?.subscription;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-30 bg-black/25 backdrop-blur-[1px]" onClick={onClose} />

      {/* Panel */}
      <div className="fixed inset-y-0 right-0 z-40 w-full max-w-md bg-white dark:bg-gray-900 shadow-modal flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-brand-50 dark:bg-brand-900/30 flex items-center justify-center">
              <Building2 className="w-4.5 h-4.5 text-brand-600 dark:text-brand-400" style={{ width: 18, height: 18 }} />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900 dark:text-white">{tenant?.firm_name ?? 'Loading…'}</p>
              {tenant && <Badge status={tenant.status} showDot className="mt-0.5" />}
            </div>
          </div>
          <button onClick={onClose} className="btn-ghost p-2">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5 space-y-6">
          {loading && <PageSpinner />}
          {error && <ErrorAlert error={error} />}

          {tenant && !loading && (
            <>
              {/* Company info */}
              <section className="space-y-3.5">
                <h3 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">Company</h3>
                <Info icon={Mail} label="Email" value={tenant.company_email} />
                <Info icon={Phone} label="Phone" value={tenant.phone} />
                <Info icon={Globe} label="Website" value={tenant.website} />
                <Info icon={MapPin} label="Address"
                  value={[tenant.address_line1, tenant.city, tenant.state, tenant.country].filter(Boolean).join(', ')} />
              </section>

              {/* Subscription */}
              <section className="space-y-3">
                <h3 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">Subscription</h3>
                {sub ? (
                  <div className="rounded-xl border border-gray-100 dark:border-gray-700 p-4 space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-gray-900 dark:text-white">{sub.plan?.name}</span>
                      <Badge status={sub.status} showDot />
                    </div>
                    <div className="grid grid-cols-2 gap-2 text-xs text-gray-500 dark:text-gray-400">
                      <span>Billing: <strong className="text-gray-700 dark:text-gray-200 capitalize">{sub.billing_cycle}</strong></span>
                      <span>Trial: <strong className="text-gray-700 dark:text-gray-200">{sub.is_trial ? 'Yes' : 'No'}</strong></span>
                      {sub.trial_expires_at && <span>Trial ends: <strong className="text-gray-700 dark:text-gray-200">{sub.trial_expires_at}</strong></span>}
                      {sub.ends_at && <span>Renews: <strong className="text-gray-700 dark:text-gray-200">{sub.ends_at}</strong></span>}
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-400">No active subscription.</p>
                )}
              </section>

              {/* Usage */}
              {usage && (
                <section className="space-y-3">
                  <h3 className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">Usage</h3>
                  <div className="space-y-2">
                    {[
                      { label: 'Leads', data: usage.leads },
                      { label: 'Users', data: usage.users },
                      { label: 'Campaigns', data: usage.campaigns },
                    ].map(({ label, data }) => {
                      if (!data) return null;
                      const pct = data.limit === 0 ? 0 : Math.round((data.current / data.limit) * 100);
                      return (
                        <div key={label}>
                          <div className="flex justify-between text-xs text-gray-600 dark:text-gray-300 mb-1">
                            <span>{label}</span>
                            <span className="font-medium">{data.current} / {data.limit === 0 ? '∞' : data.limit}</span>
                          </div>
                          {data.limit > 0 && (
                            <div className="h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
                              <div
                                className={`h-full rounded-full transition-all ${pct >= 90 ? 'bg-red-400' : pct >= 70 ? 'bg-amber-400' : 'bg-brand-500'}`}
                                style={{ width: `${Math.min(pct, 100)}%` }}
                              />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        {tenant && (
          <div className="px-6 py-4 border-t border-gray-100 dark:border-gray-700 flex gap-3">
            <Link
              to={`/tenants/${tenantId}`}
              onClick={onClose}
              className="btn-primary flex-1 justify-center"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              Open full detail
            </Link>
            <Link
              to={`/billing?tenant_id=${tenantId}`}
              onClick={onClose}
              className="btn-ghost"
            >
              <CreditCard className="w-4 h-4" />
            </Link>
          </div>
        )}
      </div>
    </>
  );
}
