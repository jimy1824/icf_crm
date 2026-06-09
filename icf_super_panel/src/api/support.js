import { api } from './client.js';

const BASE = '/support/tickets';

function qs(params = {}) {
  const clean = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== '' && v !== null),
  );
  const s = new URLSearchParams(clean).toString();
  return s ? `?${s}` : '';
}

export const supportApi = {
  // ── List / Create ──────────────────────────────────────────────────────────
  listTickets: (params = {}) => api.get(`${BASE}/${qs(params)}`),
  createTicket: (data) => api.post(`${BASE}/`, data),

  // ── Single ticket ──────────────────────────────────────────────────────────
  getTicket: (id) => api.get(`${BASE}/${id}/`),
  updateTicket: (id, data) => api.patch(`${BASE}/${id}/update/`, data),

  // ── Stats ──────────────────────────────────────────────────────────────────
  getStats: (params = {}) => api.get(`${BASE}/stats/${qs(params)}`),

  // ── Status transition ──────────────────────────────────────────────────────
  transitionStatus: (id, newStatus) =>
    api.post(`${BASE}/${id}/status/`, { status: newStatus }),

  // ── Assignment ─────────────────────────────────────────────────────────────
  assignTicket: (id, assigneeId) =>
    api.post(`${BASE}/${id}/assign/`, { assignee_id: assigneeId }),

  // ── Comments ───────────────────────────────────────────────────────────────
  getComments: (id) => api.get(`${BASE}/${id}/comments/`),
  addComment: (id, body, isInternal = false) =>
    api.post(`${BASE}/${id}/comments/`, { body, is_internal: isInternal }),

  // ── Staff list (for assignment dropdown) ───────────────────────────────────
  listStaff: () => api.get('/support/staff/'),
};
