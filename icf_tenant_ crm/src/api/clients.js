import { api } from './client.js';

const BASE = '/clients';

export const clientsApi = {
  list:        (params = {}) => api.get(`${BASE}/?${new URLSearchParams(params)}`),
  get:         (id)          => api.get(`${BASE}/${id}/`),
  getTimeline: (id)          => api.get(`${BASE}/${id}/timeline/`),
  addNote:     (id, note, isPrivate) =>
    api.post(`${BASE}/${id}/timeline/`, { note, is_private: isPrivate }),
};
