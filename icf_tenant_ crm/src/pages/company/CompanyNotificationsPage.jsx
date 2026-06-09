import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, Check, Mail, MessageSquare, Smartphone, Monitor } from 'lucide-react';
import { getNotificationPreferences, updateNotificationPreferences } from '../../api/company.js';
import PageHeader from '../../components/ui/PageHeader.jsx';

const EVENT_GROUPS = {
  'Leads & Pipeline': [
    { type: 'lead.assigned', label: 'Lead Assigned to Me' },
    { type: 'lead.status_changed', label: 'Lead Status Changed' },
    { type: 'lead.note_added', label: 'Note Added to Lead' },
    { type: 'kanban.card_moved', label: 'Kanban Card Moved' },
  ],
  'Communications': [
    { type: 'communication.inbound', label: 'Inbound Communication' },
    { type: 'communication.bounce', label: 'Email Bounced' },
    { type: 'meeting.scheduled', label: 'Meeting Scheduled' },
    { type: 'meeting.reminder', label: 'Meeting Reminder' },
  ],
  'Campaigns': [
    { type: 'campaign.launched', label: 'Campaign Launched' },
    { type: 'campaign.completed', label: 'Campaign Completed' },
    { type: 'campaign.lead_responded', label: 'Lead Responded to Campaign' },
  ],
  'System': [
    { type: 'billing.invoice_generated', label: 'Invoice Generated' },
    { type: 'billing.payment_failed', label: 'Payment Failed' },
    { type: 'user.invited', label: 'New User Invited' },
    { type: 'subscription.trial_expiring', label: 'Trial Expiring Soon' },
  ],
};

const ALL_EVENTS = Object.values(EVENT_GROUPS).flat().map((e) => e.type);

const CHANNEL_ICONS = {
  email_enabled: Mail,
  sms_enabled: MessageSquare,
  in_app_enabled: Monitor,
  push_enabled: Smartphone,
};

const CHANNEL_LABELS = {
  email_enabled: 'Email',
  sms_enabled: 'SMS',
  in_app_enabled: 'In-App',
  push_enabled: 'Push',
};

export default function CompanyNotificationsPage() {
  const qc = useQueryClient();
  const [prefs, setPrefs] = useState({});
  const [dirty, setDirty] = useState(false);
  const [saveStatus, setSaveStatus] = useState('');

  const { data, isLoading } = useQuery({
    queryKey: ['notification-preferences'],
    queryFn: getNotificationPreferences,
  });

  // Hydrate local state from API data
  useEffect(() => {
    if (!data) return;
    const map = {};
    for (const event_type of ALL_EVENTS) {
      const existing = data.find((p) => p.event_type === event_type);
      map[event_type] = {
        email_enabled: existing?.email_enabled ?? true,
        sms_enabled: existing?.sms_enabled ?? false,
        in_app_enabled: existing?.in_app_enabled ?? true,
        push_enabled: existing?.push_enabled ?? false,
      };
    }
    setPrefs(map);
    setDirty(false);
  }, [data]);

  const saveMutation = useMutation({
    mutationFn: (preferences) => updateNotificationPreferences(preferences),
    onMutate: () => setSaveStatus('saving'),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notification-preferences'] });
      setDirty(false);
      setSaveStatus('saved');
      setTimeout(() => setSaveStatus(''), 2000);
    },
    onError: () => setSaveStatus(''),
  });

  const toggle = (event_type, channel) => {
    setPrefs((p) => ({
      ...p,
      [event_type]: { ...p[event_type], [channel]: !p[event_type][channel] },
    }));
    setDirty(true);
  };

  const handleSave = () => {
    const preferences = Object.entries(prefs).map(([event_type, channels]) => ({
      event_type,
      ...channels,
    }));
    saveMutation.mutate(preferences);
  };

  const channels = Object.keys(CHANNEL_ICONS);

  return (
    <div>
      <PageHeader
        title="Notification Configuration"
        subtitle="Choose how you receive alerts for each event type"
        icon={Bell}
        actions={
          dirty && (
            <button
              onClick={handleSave}
              disabled={saveMutation.isPending}
              className="btn-primary btn-sm"
            >
              {saveMutation.isPending ? 'Saving…' : 'Save Preferences'}
            </button>
          )
        }
      />

      {saveStatus === 'saved' && (
        <div className="flex items-center gap-2 mt-4 p-3 bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300 rounded-xl text-sm">
          <Check className="w-4 h-4" />
          Preferences saved.
        </div>
      )}

      {isLoading ? (
        <div className="card p-6 mt-5 space-y-3">
          {[1, 2, 3, 4, 5].map((i) => <div key={i} className="skeleton h-4 rounded w-full" />)}
        </div>
      ) : (
        <div className="card overflow-hidden mt-5">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-100 dark:border-gray-700">
                <th className="text-left px-5 py-3 text-gray-500 font-semibold">Event</th>
                {channels.map((ch) => {
                  const Icon = CHANNEL_ICONS[ch];
                  return (
                    <th key={ch} className="text-center px-4 py-3 text-gray-500 font-semibold whitespace-nowrap">
                      <span className="inline-flex flex-col items-center gap-1">
                        <Icon className="w-3.5 h-3.5" />
                        {CHANNEL_LABELS[ch]}
                      </span>
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
              {Object.entries(EVENT_GROUPS).map(([groupName, events]) => (
                <>
                  <tr key={groupName} className="bg-gray-50/80 dark:bg-gray-800/30">
                    <td colSpan={channels.length + 1} className="px-5 py-2 font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider text-[10px]">
                      {groupName}
                    </td>
                  </tr>
                  {events.map(({ type, label }) => (
                    <tr key={type} className="hover:bg-gray-50/60 dark:hover:bg-gray-800/40">
                      <td className="px-5 py-3 text-gray-700 dark:text-gray-200">{label}</td>
                      {channels.map((ch) => (
                        <td key={ch} className="text-center px-4 py-3">
                          <button
                            onClick={() => toggle(type, ch)}
                            className={`w-8 h-5 rounded-full transition-colors relative
                              ${prefs[type]?.[ch]
                                ? 'bg-brand-600'
                                : 'bg-gray-200 dark:bg-gray-700'}`}
                            aria-label={`Toggle ${CHANNEL_LABELS[ch]} for ${label}`}
                          >
                            <span
                              className={`absolute top-0.5 w-4 h-4 rounded-full bg-white shadow-sm transition-transform
                                ${prefs[type]?.[ch] ? 'left-3.5' : 'left-0.5'}`}
                            />
                          </button>
                        </td>
                      ))}
                    </tr>
                  ))}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dirty && (
        <div className="mt-4 flex justify-end">
          <button
            onClick={handleSave}
            disabled={saveMutation.isPending}
            className="btn-primary"
          >
            {saveMutation.isPending ? 'Saving…' : 'Save All Preferences'}
          </button>
        </div>
      )}
    </div>
  );
}
