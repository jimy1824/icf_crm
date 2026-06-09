import { api } from './client.js';

const FP = (cid) => `/financials/clients/${cid}/financial-profile`;
const GOALS = (cid) => `/financials/clients/${cid}/goals`;

export const financialsApi = {
  // Financial profile (FM-15)
  getProfile:       (cid)            => api.get(`${FP(cid)}/`),
  createProfile:    (cid, data)      => api.post(`${FP(cid)}/`, data),
  updateProfile:    (cid, data)      => api.patch(`${FP(cid)}/`, data),
  listAccounts:     (cid)            => api.get(`${FP(cid)}/accounts/`),
  addAccount:       (cid, data)      => api.post(`${FP(cid)}/accounts/add/`, data),
  removeAccount:    (cid, acId)      => api.delete(`${FP(cid)}/accounts/${acId}/`),
  listInsurance:    (cid)            => api.get(`${FP(cid)}/insurance/`),
  addInsurance:     (cid, data)      => api.post(`${FP(cid)}/insurance/add/`, data),
  removeInsurance:  (cid, polId)     => api.delete(`${FP(cid)}/insurance/${polId}/`),

  // Goals (FM-16)
  listGoals:        (cid)            => api.get(`${GOALS(cid)}/`),
  createGoal:       (cid, data)      => api.post(`${GOALS(cid)}/`, data),
  getGoal:          (cid, gid)       => api.get(`${GOALS(cid)}/${gid}/`),
  updateGoal:       (cid, gid, data) => api.patch(`${GOALS(cid)}/${gid}/`, data),
  deleteGoal:       (cid, gid)       => api.delete(`${GOALS(cid)}/${gid}/`),
  listMilestones:   (cid, gid)       => api.get(`${GOALS(cid)}/${gid}/milestones/`),
  addMilestone:     (cid, gid, data) => api.post(`${GOALS(cid)}/${gid}/milestones/`, data),
  achieveMilestone: (cid, gid, mid)  => api.post(`${GOALS(cid)}/${gid}/milestones/${mid}/achieve/`),

  // Off-track goals (advisor dashboard)
  offTrackGoals: () => api.get('/financials/goals/off-track/'),

  // Calculators (FM-21)
  listCalculators:  ()                  => api.get('/financials/calculators/'),
  runCalculator:    (data)              => api.post('/financials/calculators/', data),
  calculate:        (type, inputs)      => api.post('/financials/calculators/', { calculator_type: type, inputs }),
};
