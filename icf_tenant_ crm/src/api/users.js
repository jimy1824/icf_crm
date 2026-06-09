import { api } from './client.js';

export const usersApi = {
  list:       (params = {}) => api.get(`/users/?${new URLSearchParams(params)}`),
  me:         ()            => api.get('/users/me/'),
  get:        (id)          => api.get(`/users/${id}/`),
  create:     (data)        => api.post('/users/', data),
  update:     (id, data)    => api.patch(`/users/${id}/`, data),
  deactivate: (id)          => api.post(`/users/${id}/deactivate/`),
};
