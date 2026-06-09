import { api, setToken, clearTokens } from './client.js';

export async function login(email, password) {
  const data = await api.post('/auth/crm/token/', { email, password });
  setToken(data.access, data.refresh);
  return data;
}

export function logout() {
  clearTokens();
}

export function getMe() {
  return api.get('/auth/me/');
}

export function changePassword(oldPassword, newPassword) {
  return api.post('/auth/change-password/', { old_password: oldPassword, new_password: newPassword });
}
