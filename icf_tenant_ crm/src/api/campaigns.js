import { api } from './client.js';

export const campaignsApi = {
  list:             (params = {}) => api.get(`/campaigns/?${new URLSearchParams(params)}`),
  get:              (id)          => api.get(`/campaigns/${id}/`),
  create:           (data)        => api.post('/campaigns/', data),
  update:           (id, data)    => api.patch(`/campaigns/${id}/`, data),
  activate:         (id)          => api.post(`/campaigns/${id}/activate/`),
  pause:            (id)          => api.post(`/campaigns/${id}/pause/`),
  stop:             (id)          => api.post(`/campaigns/${id}/stop/`),
  listSteps:        (id)          => api.get(`/campaigns/${id}/steps/`),
  listEnrollments:  (cid)         => api.get(`/campaigns/${cid}/enrollments/`),
  enroll:           (cid, data)   => api.post(`/campaigns/${cid}/enrollments/`, data),
  stopEnrollment:   (eid)         => api.post(`/campaigns/enrollments/${eid}/stop/`),

  // Campaign execution timeline
  leadTimeline:       (lid)  => api.get(`/timeline/leads/${lid}/`),
  campaignTimeline:   (cid)  => api.get(`/timeline/campaigns/${cid}/`),
  enrollmentTimeline: (eid)  => api.get(`/timeline/enrollments/${eid}/`),
  advisorTimeline:    ()     => api.get('/timeline/advisor/'),
  timelineDashboard:  ()     => api.get('/timeline/dashboard/'),
};
