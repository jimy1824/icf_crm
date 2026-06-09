import { api } from './client.js';

export const auditApi = {
  list: (params = {}) => {
    const qs = new URLSearchParams(params).toString();
    return api.get(`/audit/${qs ? '?' + qs : ''}`);
  },
  get: (id) => api.get(`/audit/${id}/`),
};
