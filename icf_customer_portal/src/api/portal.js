import { api } from './client.js';

// ── Profile ────────────────────────────────────────────────────────────────

export const getPortalMe = () => api.get('/portal/me/');
export const updatePortalMe = (data) => api.patch('/portal/me/', data);

// ── Dashboard ──────────────────────────────────────────────────────────────

export const getDashboard = () => api.get('/portal/dashboard/');
export const getFinancialSummary = () => api.get('/portal/financial-summary/');

// ── Goals ──────────────────────────────────────────────────────────────────

export const getGoals = () => api.get('/portal/goals/');
export const getGoal = (pk) => api.get(`/portal/goals/${pk}/`);

// ── Documents ─────────────────────────────────────────────────────────────

export const getDocuments = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return api.get(`/portal/documents/${qs ? `?${qs}` : ''}`);
};
export const getDocument = (pk) => api.get(`/portal/documents/${pk}/`);
export const uploadDocument = (payload) => api.post('/portal/documents/', payload);

// ── Meetings ───────────────────────────────────────────────────────────────

export const getMeetings = () => api.get('/portal/meetings/');
export const rsvpMeeting = (pk, rsvp) => api.patch(`/portal/meetings/${pk}/rsvp/`, { rsvp });

// ── Messages ───────────────────────────────────────────────────────────────

export const getMessages = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return api.get(`/portal/messages/${qs ? `?${qs}` : ''}`);
};
export const sendMessage = (payload) => api.post('/portal/messages/', payload);

// ── Notifications ──────────────────────────────────────────────────────────

export const getNotifications = (params = {}) => {
  const qs = new URLSearchParams(params).toString();
  return api.get(`/portal/notifications/${qs ? `?${qs}` : ''}`);
};
export const getNotificationUnreadCount = () => api.get('/portal/notifications/unread-count/');
export const markNotificationRead = (pk) => api.post(`/portal/notifications/${pk}/read/`, {});
export const markAllNotificationsRead = () => api.post('/portal/notifications/read-all/', {});

// ── Advisors ───────────────────────────────────────────────────────────────

export const getAdvisors = () => api.get('/portal/advisors/');

// ── Consent ────────────────────────────────────────────────────────────────

export const getConsent = () => api.get('/portal/consent/');
export const updateConsent = (payload) => api.post('/portal/consent/', payload);

// ── Household ─────────────────────────────────────────────────────────────

export const getHousehold = () => api.get('/portal/household/');
