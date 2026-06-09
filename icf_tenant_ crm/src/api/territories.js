import { api } from './client.js';

export const territoriesApi = {
  list:              (params = {}) => api.get(`/territories/?${new URLSearchParams(params)}`),
  get:               (id)          => api.get(`/territories/${id}/`),
  create:            (data)        => api.post('/territories/', data),
  update:            (id, data)    => api.patch(`/territories/${id}/`, data),
  delete:            (id)          => api.delete(`/territories/${id}/`),
  // Advisor assignment
  listAdvisors:      (id)          => api.get(`/territories/${id}/advisors/`),
  advisors:          (id)          => api.get(`/territories/${id}/advisors/`),
  assignAdvisor:     (id, advId)   => api.post(`/territories/${id}/assign-advisor/`, { advisor_id: advId }),
  unassignAdvisor:   (id, advId)   => api.delete(`/territories/${id}/advisors/${advId}/`),
  removeAdvisor:     (id, advId)   => api.delete(`/territories/${id}/advisors/${advId}/`),
  advisorTerritories:(advId)       => api.get(`/territories/advisor/${advId}/`),
  // Analytics
  analytics:         (id)          => api.get(`/territories/${id}/analytics/summary/`),
  summary:           (id)          => api.get(`/territories/${id}/analytics/summary/`),
  weeklyTrend:       (id)          => api.get(`/territories/${id}/analytics/weekly/`),
  weekly:            (id)          => api.get(`/territories/${id}/analytics/weekly/`),
  graphLeads:        ()            => api.get('/territories/analytics/graph/leads/'),
  graphAdvisors:     ()            => api.get('/territories/analytics/graph/advisors/'),
  graphWeekly:       ()            => api.get('/territories/analytics/graph/weekly-trend/'),
  graphCampaigns:    ()            => api.get('/territories/analytics/graph/campaigns/'),
  graphConversion:   ()            => api.get('/territories/analytics/graph/conversion/'),
};
