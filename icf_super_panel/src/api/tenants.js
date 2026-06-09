import { api } from './client.js';

export const tenantsApi = {
  list: () => api.get('/tenants/'),
  get: (id) => api.get(`/tenants/${id}/`),
  create: (data) => api.post('/tenants/', data),
  update: (id, data) => api.patch(`/tenants/${id}/`, data),
  suspend: (id) => api.post(`/tenants/${id}/suspend/`),
  activate: (id) => api.post(`/tenants/${id}/activate/`),
  disableLogin: (id) => api.post(`/tenants/${id}/disable-login/`),
  enableLogin: (id) => api.post(`/tenants/${id}/enable-login/`),
  extendTrial: (id, days) => api.post(`/tenants/${id}/extend-trial/`, { days }),
  usage: (id) => api.get(`/tenants/${id}/usage/`),
  getBranding: (id) => api.get(`/tenants/${id}/branding/`),
  updateBranding: (id, data) => api.patch(`/tenants/${id}/branding/`, data),
};

export const plansApi = {
  list: () => api.get('/tenants/plans/'),
  create: (data) => api.post('/tenants/plans/', data),
};

export const subscriptionsApi = {
  get: (id) => api.get(`/tenants/subscriptions/${id}/`),
  assignPlan: (id, planId) => api.post(`/tenants/subscriptions/${id}/assign-plan/`, { plan_id: planId }),
  startTrial: (id, planId, trialDays) =>
    api.post(`/tenants/subscriptions/${id}/start-trial/`, { plan_id: planId, trial_days: trialDays }),
};

export const billingApi = {
  list: (tenantId) => {
    const qs = tenantId ? `?tenant_id=${tenantId}` : '';
    return api.get(`/tenants/billing/${qs}`);
  },
  get: (id) => api.get(`/tenants/billing/${id}/`),
  create: (data) => api.post('/tenants/billing/', data),
  recordPayment: (id, data) => api.post(`/tenants/billing/${id}/record-payment/`, data),
};
