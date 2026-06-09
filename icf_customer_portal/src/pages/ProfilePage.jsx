import { useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Lock, Save, User } from 'lucide-react';
import toast from 'react-hot-toast';
import { getPortalMe, updatePortalMe } from '../api/portal.js';
import PageHeader from '../components/ui/PageHeader.jsx';
import Badge from '../components/ui/Badge.jsx';
import { PageSpinner } from '../components/ui/Spinner.jsx';

const STATUS_LABELS = {
  new: 'New Lead',
  contacted: 'Contacted',
  qualified: 'Qualified',
  in_discussion: 'In Discussion',
  proposal_sent: 'Proposal Sent',
  prospect: 'Prospect',
  client: 'Active Client',
  former_client: 'Former Client',
};

const STATUS_VARIANTS = {
  client: 'emerald',
  prospect: 'blue',
  former_client: 'gray',
};

// BRU-14: only phone and timezone are editable
const schema = z.object({
  phone: z.string().optional().or(z.literal('')),
  preferred_timezone: z.string().min(1, 'Please select a timezone'),
});

// Reasonable IANA timezone subset for US financial clients
const TIMEZONES = [
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

const TZ_LABELS = {
  'America/New_York': 'Eastern Time (ET)',
  'America/Chicago': 'Central Time (CT)',
  'America/Denver': 'Mountain Time (MT)',
  'America/Los_Angeles': 'Pacific Time (PT)',
  'America/Phoenix': 'Arizona (no DST)',
  'America/Anchorage': 'Alaska Time (AKT)',
  'Pacific/Honolulu': 'Hawaii Time (HST)',
  'America/Puerto_Rico': 'Atlantic Time (AT)',
  'UTC': 'UTC',
};

function ReadOnlyField({ label, value }) {
  return (
    <div>
      <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">{label}</label>
      <p className="text-sm font-medium text-gray-800 dark:text-gray-200 py-2">{value || '—'}</p>
    </div>
  );
}

export default function ProfilePage() {
  const queryClient = useQueryClient();

  const { data: profile, isLoading } = useQuery({
    queryKey: ['portal-me'],
    queryFn: getPortalMe,
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isDirty, isSubmitting },
  } = useForm({
    resolver: zodResolver(schema),
    defaultValues: { phone: '', preferred_timezone: 'America/New_York' },
  });

  // Populate form when profile loads
  useEffect(() => {
    if (profile) {
      reset({
        phone: profile.phone || '',
        preferred_timezone: profile.preferred_timezone || 'America/New_York',
      });
    }
  }, [profile, reset]);

  const mutation = useMutation({
    mutationFn: updatePortalMe,
    onSuccess: (data) => {
      toast.success('Profile updated successfully');
      queryClient.setQueryData(['portal-me'], data);
      reset({ phone: data.phone || '', preferred_timezone: data.preferred_timezone || 'America/New_York' });
    },
    onError: (err) => {
      toast.error(err.message || 'Failed to update profile');
    },
  });

  function onSubmit(values) {
    mutation.mutate(values);
  }

  if (isLoading) return <PageSpinner />;

  const statusLabel = STATUS_LABELS[profile?.status] ?? profile?.status ?? 'Lead';
  const statusVariant = STATUS_VARIANTS[profile?.status] ?? 'amber';

  return (
    <div>
      <PageHeader
        title="My Profile"
        subtitle="Your personal information and contact preferences"
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Read-only personal info */}
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-9 h-9 rounded-lg bg-brand-50 dark:bg-brand-900/20 flex items-center justify-center">
              <User className="w-4 h-4 text-brand-600 dark:text-brand-400" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Personal Information</h2>
              <div className="flex items-center gap-1 mt-0.5">
                <Lock className="w-3 h-3 text-gray-400" />
                <p className="text-[10px] text-gray-400">Managed by your advisor</p>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <ReadOnlyField label="First Name" value={profile?.first_name} />
            <ReadOnlyField label="Last Name" value={profile?.last_name} />
            <ReadOnlyField label="Email Address" value={profile?.email} />
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Relationship Status</label>
              <div className="py-1">
                <Badge variant={statusVariant}>{statusLabel}</Badge>
              </div>
            </div>
          </div>

          <div className="mt-5 pt-4 border-t border-gray-100 dark:border-gray-700">
            <p className="text-xs text-gray-400 dark:text-gray-500">
              Personal information is managed by your advisor. Contact them to update your name or email.
            </p>
          </div>
        </div>

        {/* Editable preferences (BRU-14: phone + timezone only) */}
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-9 h-9 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 flex items-center justify-center">
              <Save className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            </div>
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Contact Preferences</h2>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            {/* Phone */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Phone Number
              </label>
              <input
                type="tel"
                placeholder="+1 (555) 000-0000"
                className={`input ${errors.phone ? 'border-red-400' : ''}`}
                {...register('phone')}
              />
              {errors.phone && (
                <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.phone.message}</p>
              )}
            </div>

            {/* Timezone */}
            <div>
              <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1.5">
                Preferred Timezone <span className="text-red-500">*</span>
              </label>
              <select
                className={`select ${errors.preferred_timezone ? 'border-red-400' : ''}`}
                {...register('preferred_timezone')}
              >
                {TIMEZONES.map((tz) => (
                  <option key={tz} value={tz}>{TZ_LABELS[tz] ?? tz}</option>
                ))}
              </select>
              {errors.preferred_timezone && (
                <p className="mt-1 text-xs text-red-600 dark:text-red-400">{errors.preferred_timezone.message}</p>
              )}
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="submit"
                disabled={!isDirty || isSubmitting || mutation.isPending}
                className="btn-primary"
              >
                {mutation.isPending ? (
                  <div className="w-4 h-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                ) : (
                  <Save className="w-4 h-4" />
                )}
                Save Changes
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
