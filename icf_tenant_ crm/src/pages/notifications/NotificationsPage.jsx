import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import toast from 'react-hot-toast';
import { Bell, Check, CheckCheck } from 'lucide-react';
import { notificationsApi } from '../../api/notifications.js';
import { useDispatch } from 'react-redux';
import { setNotificationCount } from '../../store/uiSlice.js';
import PageHeader from '../../components/ui/PageHeader.jsx';
import { SkeletonRow } from '../../components/ui/Spinner.jsx';
import Spinner from '../../components/ui/Spinner.jsx';
import EmptyState from '../../components/ui/EmptyState.jsx';

export default function NotificationsPage() {
  const dispatch = useDispatch();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ['notifications', 'all'],
    queryFn: () => notificationsApi.list(),
  });

  const markRead = useMutation({
    mutationFn: (id) => notificationsApi.markRead(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] });
      qc.invalidateQueries({ queryKey: ['notifications-unread-count'] });
    },
  });

  const markAll = useMutation({
    mutationFn: () => notificationsApi.markAllRead(),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notifications'] });
      qc.invalidateQueries({ queryKey: ['notifications-unread-count'] });
      dispatch(setNotificationCount(0));
      toast.success('All marked as read');
    },
    onError: (e) => toast.error(e.message),
  });

  const notifications = data?.results ?? data ?? [];
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return (
    <div>
      <PageHeader
        title="Notifications"
        icon={Bell}
        subtitle={unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}
        actions={
          unreadCount > 0 && (
            <button onClick={() => markAll.mutate()} className="btn-outline btn-sm" disabled={markAll.isPending}>
              {markAll.isPending ? <Spinner size="sm" /> : <CheckCheck className="w-3.5 h-3.5" />}
              Mark All Read
            </button>
          )
        }
      />

      <div className="card overflow-hidden">
        {isLoading && (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {[1,2,3,4,5].map((i) => <SkeletonRow key={i} cols={3} />)}
          </div>
        )}
        {!isLoading && notifications.length > 0 ? (
          <div className="divide-y divide-gray-100 dark:divide-gray-800">
            {notifications.map((n) => (
              <div key={n.id}
                className={`flex items-start gap-4 px-5 py-4 transition-colors hover:bg-gray-50/60 dark:hover:bg-gray-800/60
                  ${!n.is_read ? 'bg-brand-50/50 dark:bg-brand-900/10' : ''}`}>
                <div className={`w-2 h-2 rounded-full mt-2 flex-shrink-0 ${!n.is_read ? 'bg-brand-500' : 'bg-transparent'}`} />
                <div className="flex-1 min-w-0">
                  <p className={`text-sm ${!n.is_read ? 'font-semibold text-gray-900 dark:text-white' : 'text-gray-700 dark:text-gray-300'}`}>
                    {n.title ?? n.message}
                  </p>
                  {n.body && n.body !== n.title && (
                    <p className="text-xs text-gray-500 mt-0.5">{n.body}</p>
                  )}
                  <p className="text-[10px] text-gray-400 mt-1">{n.created_at?.slice(0,16).replace('T',' ')}</p>
                </div>
                {!n.is_read && (
                  <button onClick={() => markRead.mutate(n.id)}
                    className="flex-shrink-0 text-gray-400 hover:text-brand-500 transition-colors mt-1"
                    title="Mark as read">
                    <Check className="w-4 h-4" />
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : !isLoading ? (
          <EmptyState icon={Bell} title="No notifications" subtitle="You're all caught up!" />
        ) : null}
      </div>
    </div>
  );
}
