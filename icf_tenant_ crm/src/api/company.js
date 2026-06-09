import { api } from './client.js';

function qs(params) {
  if (!params) return '';
  const filtered = Object.fromEntries(
    Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
  );
  const str = new URLSearchParams(filtered).toString();
  return str ? `?${str}` : '';
}

// Company settings (own tenant profile)
export const getCompanySettings = () => api.get('/tenants/company/settings/');
export const updateCompanySettings = (data) => api.patch('/tenants/company/settings/', data);
export const updateCompanyLogo = (logo_url) => api.patch('/tenants/company/logo/', { logo_url });

// Tenant usage (subscription limits)
export const getCompanyUsage = (tenantId) => api.get(`/tenants/${tenantId}/usage/`);

// Branding
export const getCompanyBranding = (tenantId) => api.get(`/tenants/${tenantId}/branding/`);
export const updateCompanyBranding = (tenantId, data) => api.patch(`/tenants/${tenantId}/branding/`, data);

// Billing records (own tenant)
export const getBillingRecords = (params) => api.get(`/tenants/billing/${qs(params)}`);

// Subscription info
export const getSubscription = (subscriptionId) => api.get(`/tenants/subscriptions/${subscriptionId}/`);

// Notification preferences (own user)
export const getNotificationPreferences = () => api.get('/tenants/company/notification-preferences/');
export const updateNotificationPreferences = (preferences) =>
  api.put('/tenants/company/notification-preferences/', { preferences });

// Employees
export const getEmployees = (params) => api.get(`/employees/${qs(params)}`);
export const createEmployee = (data) => api.post('/employees/', data);
export const deactivateEmployee = (id) => api.post(`/employees/${id}/deactivate/`);
export const assignEmployeeRole = (id, role_slug) => api.post(`/employees/${id}/assign-role/`, { role_slug });

// Territories (company view — all territories)
export const getTerritories = (params) => api.get(`/territories/${qs(params)}`);
export const createTerritory = (data) => api.post('/territories/', data);
export const updateTerritory = (id, data) => api.patch(`/territories/${id}/`, data);
export const deleteTerritory = (id) => api.delete(`/territories/${id}/`);
export const getTerritoryAdvisors = (id) => api.get(`/territories/${id}/advisors/`);
export const assignAdvisorToTerritory = (id, advisor_id) =>
  api.post(`/territories/${id}/assign-advisor/`, { advisor_id });
export const removeAdvisorFromTerritory = (territoryId, advisorId) =>
  api.delete(`/territories/${territoryId}/advisors/${advisorId}/`);

// Timezone
export const getTenantTimezone = () => api.get('/timezones/tenant/');
export const updateTenantTimezone = (data) => api.patch('/timezones/tenant/', data);
export const getAdvisorTimezone = () => api.get('/timezones/advisor/');
export const setAdvisorTimezone = (timezone) => api.put('/timezones/advisor/', { timezone });

// Support tickets
export const getSupportTickets = (params) => api.get(`/support/tickets/${qs(params)}`);
export const getSupportTicketStats = () => api.get('/support/tickets/stats/');
export const createSupportTicket = (data) => api.post('/support/tickets/', data);
export const getSupportTicket = (id) => api.get(`/support/tickets/${id}/`);
export const updateSupportTicket = (id, data) => api.patch(`/support/tickets/${id}/update/`, data);
export const updateTicketStatus = (id, status) => api.post(`/support/tickets/${id}/status/`, { status });
export const getTicketComments = (id) => api.get(`/support/tickets/${id}/comments/`);
export const addTicketComment = (id, body) => api.post(`/support/tickets/${id}/comments/`, { body });

// Roles & Permissions (read from employees app)
export const getRoles = (params) => api.get(`/employees/roles/${qs(params)}`);
export const getPermissions = () => api.get('/employees/permissions/');
