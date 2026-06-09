import { api } from './client.js';

export async function login(email, password) {
  const data = await api.post('/auth/super/token/', { email, password });
  localStorage.setItem('access_token', data.access);
  localStorage.setItem('refresh_token', data.refresh);
  return data;
}

export async function refreshToken() {
  const refresh = localStorage.getItem('refresh_token');
  const res = await fetch('/api/v1/auth/token/refresh/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) throw new Error('Session expired');
  const data = await res.json();
  localStorage.setItem('access_token', data.access);
  return data.access;
}

export async function getMe() {
  return api.get('/auth/me/');
}

export function logout() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}
