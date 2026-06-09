import { api } from './client.js';

export const communicationsApi = {
  // Communications timeline (FM-10)
  timeline:     (params = {}) => {
    const clean = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined)
    );
    return api.get(`/communications/timeline/?${new URLSearchParams(clean)}`);
  },
  listTimeline: (params = {}) => {
    const clean = Object.fromEntries(
      Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined)
    );
    return api.get(`/communications/timeline/?${new URLSearchParams(clean)}`);
  },
  // Advisor sends a message to a lead (FM-10)
  send: (data) => api.post('/communications/send/', data),

  // Mailbox (FM-07)
  listMailboxes:  ()     => api.get('/communications/mailboxes/'),
  connectMailbox: (data) => api.post('/communications/mailboxes/', data),

  // Trigger domains (BRU-02)
  listTriggerDomains:  ()     => api.get('/communications/trigger-domains/'),
  addTriggerDomain:    (data) => api.post('/communications/trigger-domains/', data),

  // Calls (FM-20)
  listCalls:     (params = {}) => api.get(`/communications/calls/?${new URLSearchParams(params)}`),
  logCall:       (data)        => api.post('/communications/calls/', data),
  recordOutcome: (id, data)    => api.patch(`/communications/calls/${id}/outcome/`, data),
  callOutcome:   (id, data)    => api.patch(`/communications/calls/${id}/outcome/`, data),

  // Meetings (FM-19)
  listMeetings:    (params = {}) => api.get(`/communications/meetings/?${new URLSearchParams(params)}`),
  createMeeting:   (data)        => api.post('/communications/meetings/', data),
  getMeeting:      (id)          => api.get(`/communications/meetings/${id}/`),
  meetingOutcome:       (id, data) => api.patch(`/communications/meetings/${id}/outcome/`, data),
  recordMeetingOutcome: (id, data) => api.patch(`/communications/meetings/${id}/outcome/`, data),

  // Consent (FM-24)
  listConsent:  (params = {}) => api.get(`/communications/consent/?${new URLSearchParams(params)}`),
  addConsent:   (data)        => api.post('/communications/consent/', data),

  // Suppression (FM-25)
  listSuppression:   ()     => api.get('/communications/suppression/'),
  addSuppression:    (data) => api.post('/communications/suppression/', data),
  removeSuppression: (id)   => api.delete(`/communications/suppression/${id}/`),
};
