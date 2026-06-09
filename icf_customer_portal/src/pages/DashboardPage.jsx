import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { Bell, Calendar, MessageSquare, Target, TrendingUp, Upload } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { getDashboard, getMessages, getGoals, getMeetings } from '../api/portal.js';
import KpiCard from '../components/ui/KpiCard.jsx';
import PageHeader from '../components/ui/PageHeader.jsx';
import Badge from '../components/ui/Badge.jsx';
import EmptyState from '../components/ui/EmptyState.jsx';
import { useAuth } from '../context/AuthContext.jsx';

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

const CHANNEL_VARIANTS = {
  email: 'blue',
  EMAIL: 'blue',
  sms: 'green',
  SMS: 'green',
  portal: 'purple',
  PORTAL: 'purple',
  call: 'amber',
  CALL: 'amber',
};

function ChannelBadge({ channel }) {
  return (
    <Badge variant={CHANNEL_VARIANTS[channel] ?? 'gray'}>
      {(channel || 'N/A').toUpperCase()}
    </Badge>
  );
}

function GoalProgressBar({ goal }) {
  const pct = Math.min(100, Math.max(0, goal.progress_percentage ?? 0));
  const isOffTrack = goal.is_off_track;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-700 dark:text-gray-300 truncate flex-1 mr-2">{goal.title}</span>
        <span className={`text-[10px] font-semibold ${isOffTrack ? 'text-amber-600 dark:text-amber-400' : 'text-emerald-600 dark:text-emerald-400'}`}>
          {pct.toFixed(0)}%
        </span>
      </div>
      <div className="h-1.5 bg-gray-100 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${isOffTrack ? 'bg-amber-400' : 'bg-emerald-500'}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const { data: dashboard, isLoading: dashLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
  });

  const { data: messagesData } = useQuery({
    queryKey: ['messages', 'recent'],
    queryFn: () => getMessages({ page: 1, page_size: 5 }),
  });

  const { data: goalsData } = useQuery({
    queryKey: ['goals', 'dashboard'],
    queryFn: getGoals,
  });

  const { data: meetingsData } = useQuery({
    queryKey: ['meetings', 'dashboard'],
    queryFn: getMeetings,
  });

  const messages = messagesData?.results ?? [];
  const goals = goalsData?.results ?? goalsData ?? [];
  const allMeetings = meetingsData?.results ?? meetingsData ?? [];
  const upcomingMeetings = allMeetings.filter((m) => {
    if (!m.scheduled_at) return false;
    return new Date(m.scheduled_at) >= new Date();
  });
  const nextMeeting = upcomingMeetings[0];

  const statusLabel = STATUS_LABELS[dashboard?.lead_status ?? user?.status] ?? 'Lead';

  return (
    <div>
      <PageHeader
        title={`Welcome back, ${user?.first_name ?? 'there'}`}
        subtitle="Here's a summary of your financial relationship"
      />

      {/* KPI Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
        <KpiCard
          label="Relationship Status"
          value={statusLabel}
          icon={TrendingUp}
          loading={dashLoading}
          accent="brand"
        />
        <KpiCard
          label="Active Goals"
          value={dashboard?.goals_count ?? '—'}
          sub={dashboard?.off_track_goals ? `${dashboard.off_track_goals} off track` : 'All on track'}
          icon={Target}
          loading={dashLoading}
          accent="emerald"
        />
        <KpiCard
          label="Upcoming Meetings"
          value={dashboard?.upcoming_meetings_count ?? '—'}
          icon={Calendar}
          loading={dashLoading}
          accent="brand"
        />
        <KpiCard
          label="Unread Notifications"
          value={dashboard?.unread_notifications_count ?? '—'}
          icon={Bell}
          loading={dashLoading}
          accent={dashboard?.unread_notifications_count > 0 ? 'amber' : 'brand'}
        />
      </div>

      {/* Main content row */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Recent Communications */}
        <div className="xl:col-span-2 card p-0 overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 dark:border-gray-700">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Recent Communications</h2>
            <button
              onClick={() => navigate('/messages')}
              className="text-xs text-brand-600 dark:text-brand-400 hover:underline font-medium"
            >
              View all
            </button>
          </div>
          <div>
            {messages.length === 0 ? (
              <EmptyState
                icon={MessageSquare}
                title="No communications yet"
                description="Your advisor will be in touch soon."
              />
            ) : (
              <ul className="divide-y divide-gray-50 dark:divide-gray-800">
                {messages.map((msg) => (
                  <li key={msg.id} className="px-5 py-3 flex items-start gap-3 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
                    <ChannelBadge channel={msg.channel} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-800 dark:text-gray-200 truncate">
                        {msg.subject || msg.body_preview || msg.body?.substring(0, 80) || '(no subject)'}
                      </p>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {msg.direction === 'inbound' ? 'From you' : 'From advisor'} ·{' '}
                        {msg.sent_at ? formatDistanceToNow(new Date(msg.sent_at), { addSuffix: true }) : ''}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* Right column */}
        <div className="flex flex-col gap-4">
          {/* Goals progress */}
          <div className="card p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Goals Progress</h2>
              <button
                onClick={() => navigate('/goals')}
                className="text-xs text-brand-600 dark:text-brand-400 hover:underline font-medium"
              >
                View all
              </button>
            </div>
            {goals.length === 0 ? (
              <p className="text-xs text-gray-400 dark:text-gray-500 text-center py-4">
                No goals set yet. Your advisor will create goals for you.
              </p>
            ) : (
              <div className="space-y-3">
                {goals.slice(0, 4).map((goal) => (
                  <GoalProgressBar key={goal.id} goal={goal} />
                ))}
              </div>
            )}
          </div>

          {/* Next meeting */}
          <div className="card p-5">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Next Meeting</h2>
            {!nextMeeting ? (
              <p className="text-xs text-gray-400 dark:text-gray-500">
                No upcoming meetings — your advisor will schedule one soon.
              </p>
            ) : (
              <div className="space-y-2">
                <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                  {nextMeeting.title || nextMeeting.meeting_type || 'Meeting'}
                </p>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {new Date(nextMeeting.scheduled_at).toLocaleDateString('en-US', {
                    weekday: 'long',
                    month: 'long',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </p>
                <button
                  onClick={() => navigate('/meetings')}
                  className="text-xs text-brand-600 dark:text-brand-400 hover:underline font-medium"
                >
                  View details
                </button>
              </div>
            )}
          </div>

          {/* Quick actions */}
          <div className="card p-5">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">Quick Actions</h2>
            <div className="flex flex-col gap-2">
              <button
                onClick={() => navigate('/messages')}
                className="btn-ghost w-full justify-start text-sm"
              >
                <MessageSquare className="w-4 h-4" />
                Send Message
              </button>
              <button
                onClick={() => navigate('/documents')}
                className="btn-ghost w-full justify-start text-sm"
              >
                <Upload className="w-4 h-4" />
                Upload Document
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
