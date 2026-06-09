import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { format, isPast } from 'date-fns';
import { Calendar, Check, ExternalLink, MapPin, X } from 'lucide-react';
import toast from 'react-hot-toast';
import { getMeetings, rsvpMeeting } from '../api/portal.js';
import PageHeader from '../components/ui/PageHeader.jsx';
import Badge from '../components/ui/Badge.jsx';
import EmptyState from '../components/ui/EmptyState.jsx';
import { PageSpinner } from '../components/ui/Spinner.jsx';

const RSVP_VARIANTS = {
  accepted: 'emerald',
  declined: 'red',
  pending: 'amber',
};

const STATUS_VARIANTS = {
  scheduled: 'blue',
  completed: 'emerald',
  cancelled: 'red',
  rescheduled: 'amber',
  no_show: 'gray',
};

function MeetingCard({ meeting, onRsvp, rsvpPending }) {
  const scheduled = meeting.scheduled_at ? new Date(meeting.scheduled_at) : null;
  const isPastMeeting = scheduled ? isPast(scheduled) : true;

  return (
    <div className="card p-5 space-y-3">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            {meeting.title || meeting.meeting_type || 'Meeting'}
          </h3>
          {scheduled && (
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {format(scheduled, "EEEE, MMMM d, yyyy 'at' h:mm a")}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          {meeting.status && (
            <Badge variant={STATUS_VARIANTS[meeting.status] ?? 'gray'}>
              {meeting.status}
            </Badge>
          )}
          {meeting.rsvp && (
            <Badge variant={RSVP_VARIANTS[meeting.rsvp] ?? 'gray'}>
              {meeting.rsvp}
            </Badge>
          )}
        </div>
      </div>

      {/* Location / link */}
      {meeting.location && (
        <div className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400">
          <MapPin className="w-3.5 h-3.5 flex-shrink-0" />
          <span>{meeting.location}</span>
        </div>
      )}
      {meeting.zoom_link && (
        <a
          href={meeting.zoom_link}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs text-brand-600 dark:text-brand-400 hover:underline"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          Join Video Call
        </a>
      )}

      {/* Notes/outcome */}
      {meeting.outcome_notes && (
        <p className="text-xs text-gray-500 dark:text-gray-400 italic border-l-2 border-gray-200 dark:border-gray-600 pl-3">
          {meeting.outcome_notes}
        </p>
      )}

      {/* RSVP buttons — only for upcoming meetings */}
      {!isPastMeeting && meeting.status !== 'cancelled' && (
        <div className="flex items-center gap-2 pt-1">
          <span className="text-xs text-gray-500 dark:text-gray-400 mr-1">RSVP:</span>
          <button
            onClick={() => onRsvp(meeting.id, 'accepted')}
            disabled={rsvpPending || meeting.rsvp === 'accepted'}
            className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              meeting.rsvp === 'accepted'
                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-emerald-50 hover:text-emerald-700 dark:hover:bg-emerald-900/30 dark:hover:text-emerald-300'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <Check className="w-3 h-3" />
            Accept
          </button>
          <button
            onClick={() => onRsvp(meeting.id, 'declined')}
            disabled={rsvpPending || meeting.rsvp === 'declined'}
            className={`inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              meeting.rsvp === 'declined'
                ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-red-50 hover:text-red-700 dark:hover:bg-red-900/30 dark:hover:text-red-300'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            <X className="w-3 h-3" />
            Decline
          </button>
        </div>
      )}
    </div>
  );
}

export default function MeetingsPage() {
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['meetings'],
    queryFn: getMeetings,
  });

  const rsvpMutation = useMutation({
    mutationFn: ({ id, rsvp }) => rsvpMeeting(id, rsvp),
    onSuccess: () => {
      toast.success('RSVP updated');
      queryClient.invalidateQueries({ queryKey: ['meetings'] });
    },
    onError: (err) => {
      toast.error(err.message || 'Failed to update RSVP');
    },
  });

  function handleRsvp(id, rsvp) {
    rsvpMutation.mutate({ id, rsvp });
  }

  const allMeetings = data?.results ?? data ?? [];
  const now = new Date();

  const upcoming = allMeetings.filter((m) => {
    if (!m.scheduled_at) return false;
    return new Date(m.scheduled_at) >= now;
  });

  const past = allMeetings.filter((m) => {
    if (!m.scheduled_at) return true;
    return new Date(m.scheduled_at) < now;
  });

  if (isLoading) return <PageSpinner />;

  return (
    <div>
      <PageHeader
        title="Meetings"
        subtitle="Your scheduled and past advisor meetings"
      />

      {isError ? (
        <div className="card p-6 text-center text-sm text-red-600 dark:text-red-400">
          Unable to load meetings. Please try again later.
        </div>
      ) : (
        <>
          {/* Upcoming */}
          <section className="mb-8">
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 uppercase tracking-wide">
              Upcoming ({upcoming.length})
            </h2>
            {upcoming.length === 0 ? (
              <div className="card">
                <EmptyState
                  icon={Calendar}
                  title="No upcoming meetings"
                  description="Your advisor will schedule a meeting soon."
                />
              </div>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {upcoming.map((m) => (
                  <MeetingCard
                    key={m.id}
                    meeting={m}
                    onRsvp={handleRsvp}
                    rsvpPending={rsvpMutation.isPending}
                  />
                ))}
              </div>
            )}
          </section>

          {/* Past */}
          <section>
            <h2 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3 uppercase tracking-wide">
              Past Meetings ({past.length})
            </h2>
            {past.length === 0 ? (
              <p className="text-sm text-gray-400 dark:text-gray-500">No past meetings recorded.</p>
            ) : (
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {past.map((m) => (
                  <MeetingCard
                    key={m.id}
                    meeting={m}
                    onRsvp={handleRsvp}
                    rsvpPending={rsvpMutation.isPending}
                  />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
