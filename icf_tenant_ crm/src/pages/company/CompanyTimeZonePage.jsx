import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Globe, Clock, Check } from 'lucide-react';
import { getTenantTimezone, updateTenantTimezone, getAdvisorTimezone, setAdvisorTimezone } from '../../api/company.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import { useAuth } from '../../hooks/useAuth.js';

const COMMON_TIMEZONES = [
  'America/New_York',
  'America/Chicago',
  'America/Denver',
  'America/Los_Angeles',
  'America/Phoenix',
  'America/Anchorage',
  'Pacific/Honolulu',
  'America/Puerto_Rico',
  'UTC',
];

function SaveIndicator({ status }) {
  if (status === 'saving') return <span className="text-xs text-gray-400">Saving…</span>;
  if (status === 'saved') return (
    <span className="text-xs text-green-600 flex items-center gap-1">
      <Check className="w-3.5 h-3.5" />Saved
    </span>
  );
  return null;
}

export default function CompanyTimeZonePage() {
  const { isFirmAdmin } = useAuth();
  const canEditTenant = isFirmAdmin();
  const qc = useQueryClient();

  const [tenantTzDraft, setTenantTzDraft] = useState('');
  const [advisorTzDraft, setAdvisorTzDraft] = useState('');
  const [tenantSaveStatus, setTenantSaveStatus] = useState('');
  const [advisorSaveStatus, setAdvisorSaveStatus] = useState('');

  const { data: tenantConfig, isLoading: tenantLoading } = useQuery({
    queryKey: ['tenant-timezone'],
    queryFn: getTenantTimezone,
  });

  const { data: advisorConfig, isLoading: advisorLoading } = useQuery({
    queryKey: ['advisor-timezone'],
    queryFn: getAdvisorTimezone,
  });

  useEffect(() => {
    if (tenantConfig?.timezone) setTenantTzDraft(tenantConfig.timezone);
  }, [tenantConfig]);

  useEffect(() => {
    if (advisorConfig?.timezone) setAdvisorTzDraft(advisorConfig.timezone);
  }, [advisorConfig]);

  const tenantMutation = useMutation({
    mutationFn: (data) => updateTenantTimezone(data),
    onMutate: () => setTenantSaveStatus('saving'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tenant-timezone'] });
      setTenantSaveStatus('saved');
      setTimeout(() => setTenantSaveStatus(''), 2000);
    },
    onError: () => setTenantSaveStatus(''),
  });

  const advisorMutation = useMutation({
    mutationFn: (tz) => setAdvisorTimezone(tz),
    onMutate: () => setAdvisorSaveStatus('saving'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['advisor-timezone'] });
      setAdvisorSaveStatus('saved');
      setTimeout(() => setAdvisorSaveStatus(''), 2000);
    },
    onError: () => setAdvisorSaveStatus(''),
  });

  return (
    <div>
      <PageHeader
        title="Time Zone"
        subtitle="Configure firm and personal timezone settings"
        icon={Globe}
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mt-5">
        {/* Tenant timezone */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-brand-50 dark:bg-brand-900/20 flex items-center justify-center">
                <Globe className="w-4 h-4 text-brand-600" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900 dark:text-white">Firm Timezone</p>
                <p className="text-xs text-gray-400">Default for all firm operations</p>
              </div>
            </div>
            <SaveIndicator status={tenantSaveStatus} />
          </div>

          {tenantLoading ? (
            <div className="skeleton h-9 rounded-lg w-full" />
          ) : (
            <>
              <select
                value={tenantTzDraft}
                onChange={(e) => setTenantTzDraft(e.target.value)}
                disabled={!canEditTenant}
                className="input w-full"
              >
                {COMMON_TIMEZONES.map((tz) => (
                  <option key={tz} value={tz}>{tz.replace(/_/g, ' ')}</option>
                ))}
              </select>
              {tenantConfig?.office_hours_start && (
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <div>
                    <label className="label">Office Hours Start</label>
                    <input
                      type="time"
                      defaultValue={tenantConfig.office_hours_start}
                      disabled={!canEditTenant}
                      className="input"
                      id="office_start"
                    />
                  </div>
                  <div>
                    <label className="label">Office Hours End</label>
                    <input
                      type="time"
                      defaultValue={tenantConfig.office_hours_end}
                      disabled={!canEditTenant}
                      className="input"
                      id="office_end"
                    />
                  </div>
                </div>
              )}
              {canEditTenant && (
                <button
                  onClick={() => tenantMutation.mutate({ timezone: tenantTzDraft })}
                  disabled={tenantMutation.isPending || tenantTzDraft === tenantConfig?.timezone}
                  className="btn-primary btn-sm mt-3 w-full"
                >
                  Save Firm Timezone
                </button>
              )}
            </>
          )}

          {!canEditTenant && (
            <p className="mt-3 text-xs text-gray-400">Only Tenant Admin can change the firm timezone.</p>
          )}
        </div>

        {/* Advisor personal override */}
        <div className="card p-5">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-purple-50 dark:bg-purple-900/20 flex items-center justify-center">
                <Clock className="w-4 h-4 text-purple-600" />
              </div>
              <div>
                <p className="text-sm font-semibold text-gray-900 dark:text-white">My Timezone</p>
                <p className="text-xs text-gray-400">Personal override for your account</p>
              </div>
            </div>
            <SaveIndicator status={advisorSaveStatus} />
          </div>

          {advisorLoading ? (
            <div className="skeleton h-9 rounded-lg w-full" />
          ) : (
            <>
              <select
                value={advisorTzDraft}
                onChange={(e) => setAdvisorTzDraft(e.target.value)}
                className="input w-full"
              >
                <option value="">Use firm default ({tenantConfig?.timezone ?? '…'})</option>
                {COMMON_TIMEZONES.map((tz) => (
                  <option key={tz} value={tz}>{tz.replace(/_/g, ' ')}</option>
                ))}
              </select>
              <button
                onClick={() => advisorMutation.mutate(advisorTzDraft || null)}
                disabled={advisorMutation.isPending}
                className="btn-primary btn-sm mt-3 w-full"
              >
                Save My Timezone
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
