import { useSelector, useDispatch } from 'react-redux';
import { loginThunk, logoutAction } from '../store/authSlice.js';

export function useAuth() {
  const { user, loading, error } = useSelector((s) => s.auth);
  const dispatch = useDispatch();

  const login = (email, password) => dispatch(loginThunk({ email, password }));
  const logout = () => dispatch(logoutAction());

  const hasRole = (...roles) => user && roles.includes(user.role);
  const isFirmAdmin = () => hasRole('tenant_admin', 'firm_admin');
  const isTeamLead  = () => hasRole('team_lead', 'senior_advisor');
  const isAdvisor   = () => hasRole('advisor');

  return { user, loading, error, login, logout, hasRole, isFirmAdmin, isTeamLead, isAdvisor };
}
