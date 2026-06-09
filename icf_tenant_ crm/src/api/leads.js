import { api } from './client.js';

const BASE = '/leads';

export const leadsApi = {
  list:       (params = {}) => {
    const clean = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined)
    );
    return api.get(`${BASE}/?${new URLSearchParams(clean)}`);
  },
  kanban:     ()            => api.get(`${BASE}/kanban/`),
  get:        (id)          => api.get(`${BASE}/${id}/`),
  create:     (data)        => api.post(`${BASE}/`, data),
  update:     (id, data)    => api.patch(`${BASE}/${id}/`, data),
  delete:     (id)          => api.delete(`${BASE}/${id}/`),
  assign:     (id, data)    => api.post(`${BASE}/${id}/assign/`, data),
  moveStage:  (id, stage)   => api.post(`${BASE}/${id}/move-stage/`, { stage }),
  getTimeline:(id)          => api.get(`${BASE}/${id}/timeline/`),
  addNote:    (id, note, isPrivate) =>
    api.post(`${BASE}/${id}/timeline/`, { note, is_private: isPrivate }),
  optOut:     (id)          => api.post(`${BASE}/${id}/opt-out/`),
  convert:    (id, data)    => api.post(`${BASE}/${id}/convert/`, data),
};
