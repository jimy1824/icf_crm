import { api } from './client.js';

export const analyticsApi = {
  platformSummary: () => api.get('/analytics/platform/'),
};
