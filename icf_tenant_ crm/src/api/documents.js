import { api } from './client.js';

export const documentsApi = {
  // List — accepts { client: cid, kyc_status: ... } params object
  list: (params = {}) => {
    const { client, ...rest } = params;
    if (client) {
      return api.get(`/documents/clients/${client}/documents/?${new URLSearchParams(rest)}`);
    }
    return api.get(`/documents/documents/?${new URLSearchParams(rest)}`);
  },

  // Upload — cid + file + docType
  upload: (cid, file, docType) => {
    const form = new FormData();
    form.append('file', file);
    form.append('document_type', docType);
    return api.upload(`/documents/clients/${cid}/documents/`, form);
  },

  get:      (cid, did)   => api.get(`/documents/clients/${cid}/documents/${did}/`),
  delete:   (did)        => api.delete(`/documents/documents/${did}/`),
  verify:   (did, data)  => api.post(`/documents/documents/${did}/verify/`, data ?? {}),
  reject:   (did, data)  => api.post(`/documents/documents/${did}/reject/`, data ?? {}),
  legalHold:(did, data)  => api.post(`/documents/documents/${did}/legal-hold/`, data ?? {}),
  kycPending: ()         => api.get('/documents/documents/kyc-pending/'),
};
