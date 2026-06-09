const BASE = '/api/v1';

function getToken() {
  return localStorage.getItem('crm_access_token');
}

export function setToken(access, refresh) {
  localStorage.setItem('crm_access_token', access);
  if (refresh) localStorage.setItem('crm_refresh_token', refresh);
}

export function clearTokens() {
  localStorage.removeItem('crm_access_token');
  localStorage.removeItem('crm_refresh_token');
}

async function refreshTokens() {
  const refresh = localStorage.getItem('crm_refresh_token');
  if (!refresh) throw new Error('No refresh token');
  const res = await fetch(`${BASE}/auth/token/refresh/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) throw new Error('Refresh failed');
  const data = await res.json();
  setToken(data.access, data.refresh ?? refresh);
  return data.access;
}

async function request(method, path, body, opts = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const token = getToken();
  if (token) headers['Authorization'] = `Bearer ${token}`;

  const fetchOpts = { method, headers };
  if (body !== undefined && !(body instanceof FormData)) {
    fetchOpts.body = JSON.stringify(body);
  } else if (body instanceof FormData) {
    delete headers['Content-Type'];
    fetchOpts.body = body;
  }

  let res = await fetch(`${BASE}${path}`, fetchOpts);

  // Attempt silent token refresh on 401
  if (res.status === 401 && !opts._retry) {
    try {
      const newToken = await refreshTokens();
      headers['Authorization'] = `Bearer ${newToken}`;
      res = await fetch(`${BASE}${path}`, { ...fetchOpts, headers });
    } catch {
      clearTokens();
      window.location.href = '/login';
      throw new Error('Session expired');
    }
  }

  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.detail || data.message || `Request failed (${res.status})`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

export const api = {
  get:    (path)        => request('GET',    path),
  post:   (path, body)  => request('POST',   path, body),
  patch:  (path, body)  => request('PATCH',  path, body),
  put:    (path, body)  => request('PUT',    path, body),
  delete: (path)        => request('DELETE', path),
  upload: (path, form)  => request('POST',   path, form),
};
