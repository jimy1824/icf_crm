import { api } from './client.js';

export const notificationsApi = {
  list:         (params = {}) => api.get(`/notifications/?${new URLSearchParams(params)}`),
  unreadCount:  ()            => api.get('/notifications/unread-count/'),
  markRead:     (id)          => api.post(`/notifications/${id}/read/`),
  markAllRead:  ()            => api.post('/notifications/read-all/'),
};
