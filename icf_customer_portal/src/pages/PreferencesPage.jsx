import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, CheckCircle, Mail, MessageSquare, Phone, Globe } from 'lucide-react';
import toast from 'react-hot-toast';
import { getConsent, updateConsent } from '../api/portal.js';
import PageHeader from '../components/ui/PageHeader.jsx';
import Badge from '../components/ui/Badge.jsx';
import { PageSpinner } from '../components/ui/Spinner.jsx';

const CHANNELS = [
  {
    key: 'email',
    label: 'Email',
    description: 'Receive communications and updates via email.',
    icon: Mail,
  },
  {
    key: 'sms',
    label: 'SMS / Text',
    description: 'Receive text message reminders and alerts.',
    icon: MessageSquare,
  },
  {
    key: 'portal',
    label: 'Portal Messages',
    description: 'Receive messages through this secure portal.',
    icon: Globe,
  },
  {
    key: 'call',
    label: 'Phone Calls',
    description: 'Receive phone calls from your advisor.',
    icon: Phone,
  },
];

const STATE_VARIANTS = {
  granted: 'emerald',
  revoked: 'red',
  pending: 'amber',
};

function ConsentCard({ channel, consent, onUpdate, isPending }) {
  const Icon = channel.icon;
  const currentState = consent?.state ?? 'pending';
  const isGranted = currentState === 'granted';

  return (
    <div className="card p-5">
      <div className="flex items-start gap-4">
        {/* Icon */}
        <div className="w-10 h-10 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center flex-shrink-0">
          <Icon className="w-5 h-5 text-gray-500 dark:text-gray-400" />
        </div>

        {/* Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-3 mb-1">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{channel.label}</h3>
            <Badge variant={STATE_VARIANTS[currentState] ?? 'gray'}>
              {currentState}
            </Badge>
          </div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-3">{channel.description}</p>

          {/* Toggle buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => onUpdate(channel.key, 'granted')}
              disabled={isPending || isGranted}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                isGranted
                  ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300 cursor-default'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-emerald-50 hover:text-emerald-700 dark:hover:bg-emerald-900/30 dark:hover:text-emerald-300'
              } disabled:opacity-60 disabled:cursor-not-allowed`}
            >
              <CheckCircle className="w-3 h-3" />
              Grant Consent
            </button>
            <button
              onClick={() => onUpdate(channel.key, 'revoked')}
              disabled={isPending || currentState === 'revoked'}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                currentState === 'revoked'
                  ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300 cursor-default'
                  : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-900/30 dark:hover:text-red-300'
              } disabled:opacity-60 disabled:cursor-not-allowed`}
            >
              <AlertCircle className="w-3 h-3" />
              Revoke Consent
            </button>
          </div>

          {/* Last updated */}
          {consent?.updated_at && (
            <p className="text-[10px] text-gray-400 mt-1.5">
              Last updated: {new Date(consent.updated_at).toLocaleDateString('en-US', {
                month: 'short', day: 'numeric', year: 'numeric',
              })}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

export default function PreferencesPage() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['consent'],
    queryFn: getConsent,
  });

  const mutation = useMutation({
    mutationFn: ({ channel, state }) =>
      updateConsent({ channel: channel.toUpperCase(), purpose: 'general', state, source: 'portal' }),
    onSuccess: () => {
      toast.success('Consent preference updated');
      queryClient.invalidateQueries({ queryKey: ['consent'] });
    },
    onError: (err) => {
      toast.error(err.message || 'Failed to update consent');
    },
  });

  function handleUpdate(channel, state) {
    mutation.mutate({ channel, state });
  }

  // Map consent records by channel for easy lookup
  const consentByChannel = {};
  const consentList = data?.results ?? data ?? [];
  consentList.forEach((c) => {
    const ch = (c.channel || '').toLowerCase();
    consentByChannel[ch] = c;
  });

  if (isLoading) return <PageSpinner />;

  return (
    <div>
      <PageHeader
        title="Communication Preferences"
        subtitle="Manage how your advisor can contact you"
      />

      {/* Legal notice */}
      <div className="mb-6 p-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-medium text-amber-800 dark:text-amber-300 mb-0.5">
            Important Notice
          </p>
          <p className="text-xs text-amber-700 dark:text-amber-400">
            Required regulatory and account communications cannot be opted out of. Revoking consent
            for a channel only affects non-essential marketing and advisory outreach.
          </p>
        </div>
      </div>

      {isError ? (
        <div className="card p-6 text-center text-sm text-red-600 dark:text-red-400">
          Unable to load consent preferences. Please try again later.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {CHANNELS.map((channel) => (
            <ConsentCard
              key={channel.key}
              channel={channel}
              consent={consentByChannel[channel.key]}
              onUpdate={handleUpdate}
              isPending={mutation.isPending}
            />
          ))}
        </div>
      )}

      <div className="mt-6 p-4 rounded-xl bg-gray-50 dark:bg-gray-800 border border-gray-100 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Your consent preferences are recorded with a timestamp and stored securely in compliance with
          applicable regulations. Changes take effect immediately.
        </p>
      </div>
    </div>
  );
}
