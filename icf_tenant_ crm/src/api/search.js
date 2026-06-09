import { api } from './client.js';

export const searchApi = {
  global: (q, params = {}) =>
    api.get(`/search/?${new URLSearchParams({ q, ...params })}`),
};
