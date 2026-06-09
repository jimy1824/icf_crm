import { api } from './client.js';

function qs(params = {}) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== '' && v !== null),
  );
  const s = new URLSearchParams(clean).toString();
  return s ? `?${s}` : '';
}

const BASE = '/support/platform-staff';

export const staffApi = {
  list: (params = {}) => api.get(`${BASE}/${qs(params)}`),
  stats: () => api.get(`${BASE}/stats/`),
  get: (id) => api.get(`${BASE}/${id}/`),
  create: (data) => api.post(`${BASE}/`, data),
  update: (id, data) => api.patch(`${BASE}/${id}/`, data),
  deactivate: (id) => api.post(`${BASE}/${id}/deactivate/`),
  activate: (id) => api.post(`${BASE}/${id}/activate/`),
};
