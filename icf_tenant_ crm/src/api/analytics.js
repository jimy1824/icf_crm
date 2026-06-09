import { api } from './client.js';

export const analyticsApi = {
  firm:     () => api.get('/analytics/dashboard/firm/'),
  advisor:  () => api.get('/analytics/dashboard/advisor/'),
  client:   (clientId) => api.get(`/analytics/dashboard/client/?client_id=${clientId}`),
  snapshots:(params = {}) => api.get(`/analytics/snapshots/?${new URLSearchParams(params)}`),

  // Advisor list for filter dropdowns (BRU-01: only this tenant's advisors)
  advisors: () => api.get('/analytics/advisors/'),

  // Dashboard Section 1: weekly lead analytics (stacked bar)
  weeklyLeads: (scope = 'my', days = 7) =>
    api.get(`/analytics/weekly-leads/?scope=${scope}&days=${days}`),

  // Dashboard Section 2: today's leads — server-side paginated table
  // params: { advisor_id, date, page, page_size, ordering, search }
  todayLeads: (params = {}) =>
    api.get(`/analytics/today-leads/?${new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ''))
    )}`),

  // Dashboard Section 3: today's scheduled activities — server-side paginated table
  // params: { advisor_id, date, page, page_size, ordering, search }
  todayActivities: (params = {}) =>
    api.get(`/analytics/today-activities/?${new URLSearchParams(
      Object.fromEntries(Object.entries(params).filter(([, v]) => v != null && v !== ''))
    )}`),

  // Dashboard Section 4: today's inbound lead responses
  todayResponses: (scope = 'my') =>
    api.get(`/analytics/today-responses/?scope=${scope}`),

  // Dashboard Section 5: territory lead distribution (horizontal bar)
  territoryDistribution: (days = 7) =>
    api.get(`/analytics/territory-distribution/?days=${days}`),
};
