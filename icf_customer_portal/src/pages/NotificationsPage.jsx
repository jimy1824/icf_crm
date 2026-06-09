import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatDistanceToNow } from 'date-fns';
import { Bell, BellOff, Check, CheckCheck, Info, AlertTriangle, Calendar, FileText } from 'lucide-react';
import toast from 'react-hot-toast';
import { getNotifications, markNotificationRead, markAllNotificationsRead } from '../api/portal.js';
import PageHeader from '../components/ui/PageHeader.jsx';
import EmptyState from '../components/ui/EmptyState.jsx';
import { PageSpinner } from '../components/ui/Spinner.jsx';

const TYPE_ICONS = {
  info: Info,
  warning: AlertTriangle,
  meeting: Calendar,
  document: FileText,
  goal: Bell,
  message: Bell,
};

const TYPE_COLORS = {
  info: 'text-blue-500 bg-blue-50 dark:bg-blue-900/20',
  warning: 'text-amber-500 bg-amber-50 dark:bg-amber-900/20',
  meeting: 'text-purple-500 bg-purple-50 dark:bg-purple-900/20',
  document: 'text-green-500 bg-green-50 dark:bg-green-900/20',
  goal: 'text-brand-500 bg-brand-50 dark:bg-brand-900/20',
  message: 'text-brand-500 bg-brand-50 dark:bg-brand-900/20',
};

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'unread', label: 'Unread' },
  { key: 'read', label: 'Read' },
];

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState('all');

  const params = {};
  if (filter === 'unread') params.is_read = false;
  if (filter === 'read') params.is_read = true;

  const { data, isLoading } = useQuery({
    queryKey: ['notifications', filter],
    queryFn: () => getNotifications(params),
  });

  const markReadMutation = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['portal-notifications-unread-count'] });
    },
    onError: (err) => {
      toast.error(err.message || 'Failed to mark as read');
    },
  });

  const markAllMutation = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: () => {
      toast.success('All notifications marked as read');
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['portal-notifications-unread-count'] });
    },
    onError: (err) => {
      toast.error(err.message || 'Failed to mark all as read');
    },
  });

  const notifications = data?.results ?? data ?? [];
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  if (isLoading) return <PageSpinner />;

  return (
    <div>
      <PageHeader
        title="Notifications"
        subtitle="Updates and alerts from your advisor"
        actions={
          unreadCount > 0 ? (
            <button
              onClick={() => markAllMutation.mutate()}
              disabled={markAllMutation.isPending}
              className="btn-ghost text-sm"
            >
              <CheckCheck className="w-4 h-4" />
              Mark all read
            </button>
          ) : null
        }
      />

      {/* Filter tabs */}
      <div className="flex items-center gap-1 mb-4 bg-gray-100 dark:bg-gray-800 rounded-lg p-1 w-fit">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              filter === f.key
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
            }`}
          >
            {f.label}
            {f.key === 'unread' && unreadCount > 0 && (
              <span className="ml-1.5 bg-red-500 text-white text-[10px] font-bold px-1 py-0.5 rounded-full">
                {unreadCount}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* List */}
      {notifications.length === 0 ? (
        <div className="card">
          <EmptyState
            icon={filter === 'unread' ? BellOff : Bell}
            title={filter === 'unread' ? 'No unread notifications' : 'No notifications'}
            description="You're all caught up!"
          />
        </div>
      ) : (
        <div className="card overflow-hidden">
          <ul className="divide-y divide-gray-50 dark:divide-gray-800">
            {notifications.map((notif) => {
              const Icon = TYPE_ICONS[notif.notification_type] ?? Bell;
              const colorClass = TYPE_COLORS[notif.notification_type] ?? TYPE_COLORS.info;

              return (
                <li
                  key={notif.id}
                  onClick={() => !notif.is_read && markReadMutation.mutate(notif.id)}
                  className={`px-5 py-4 flex items-start gap-4 transition-colors cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-800/50 ${
                    !notif.is_read ? 'border-l-4 border-brand-500' : ''
                  }`}
                >
                  {/* Icon */}
                  <div className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 ${colorClass}`}>
                    <Icon className="w-4 h-4" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2">
                      <p className={`text-sm font-medium ${notif.is_read ? 'text-gray-600 dark:text-gray-400' : 'text-gray-900 dark:text-white'}`}>
                        {notif.title}
                      </p>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        {!notif.is_read && (
                          <span className="w-2 h-2 bg-brand-500 rounded-full" />
                        )}
                        <span className="text-[10px] text-gray-400 whitespace-nowrap">
                          {notif.created_at
                            ? formatDistanceToNow(new Date(notif.created_at), { addSuffix: true })
                            : ''}
                        </span>
                      </div>
                    </div>
                    {notif.body && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
                        {notif.body}
                      </p>
                    )}
                  </div>

                  {/* Read button */}
                  {!notif.is_read && (
                    <button
                      onClick={(e) => { e.stopPropagation(); markReadMutation.mutate(notif.id); }}
                      className="flex-shrink-0 p-1.5 rounded-lg text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 hover:text-brand-600 transition-colors"
                      title="Mark as read"
                    >
                      <Check className="w-3.5 h-3.5" />
                    </button>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
