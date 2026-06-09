import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import { login as apiLogin, logout as apiLogout, getMe } from '../api/auth.js';

const TENANT_ROLES = ['tenant_admin', 'firm_admin', 'team_lead', 'senior_advisor', 'advisor'];

export const loginThunk = createAsyncThunk('auth/login', async ({ email, password }) => {
  await apiLogin(email, password);
  const user = await getMe();
  if (!TENANT_ROLES.includes(user.role)) {
    apiLogout();
    throw new Error('Access denied: Tenant CRM is for firm advisors and admins only.');
  }
  return user;
});

export const loadMe = createAsyncThunk('auth/loadMe', async () => {
  return await getMe();
});

const authSlice = createSlice({
  name: 'auth',
  initialState: {
    user: null,
    loading: false,
    error: null,
  },
  reducers: {
    logoutAction: (state) => {
      apiLogout();
      state.user = null;
      state.error = null;
    },
    clearError: (state) => { state.error = null; },
  },
  extraReducers: (builder) => {
    builder
      .addCase(loginThunk.pending,  (state) => { state.loading = true; state.error = null; })
      .addCase(loginThunk.fulfilled,(state, { payload }) => { state.user = payload; state.loading = false; })
      .addCase(loginThunk.rejected, (state, { error }) => { state.error = error.message; state.loading = false; })
      .addCase(loadMe.pending,  (state) => { state.loading = true; })
      .addCase(loadMe.fulfilled,(state, { payload }) => { state.user = payload; state.loading = false; })
      .addCase(loadMe.rejected, (state) => { state.user = null; state.loading = false; });
  },
});

export const { logoutAction, clearError } = authSlice.actions;
export default authSlice.reducer;
