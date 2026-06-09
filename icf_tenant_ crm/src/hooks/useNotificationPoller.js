import { useEffect } from 'react';
import { useDispatch } from 'react-redux';
import { useQuery } from '@tanstack/react-query';
import { notificationsApi } from '../api/notifications.js';
import { setNotificationCount } from '../store/uiSlice.js';

/**
 * Polls GET /notifications/unread-count/ every 30 s while the user is logged in.
 * Writes the count into Redux so the Topbar bell badge stays live.
 */
export function useNotificationPoller() {
  const dispatch = useDispatch();

  const { data } = useQuery({
    queryKey: ['notifications-unread-count'],
    queryFn: () => notificationsApi.unreadCount(),
    refetchInterval: 30_000,          // poll every 30 s
    refetchIntervalInBackground: false, // pause when tab is hidden
    staleTime: 20_000,
  });

  useEffect(() => {
    if (data?.unread_count !== undefined) {
      dispatch(setNotificationCount(data.unread_count));
    }
  }, [data, dispatch]);
}
