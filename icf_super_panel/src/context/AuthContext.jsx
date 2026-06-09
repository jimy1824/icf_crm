import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { getMe, login as apiLogin, logout as apiLogout } from '../api/auth.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      setLoading(false);
      return;
    }
    getMe()
      .then((me) => setUser(me))
      .catch(() => {
        apiLogout();
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    await apiLogin(email, password);
    const me = await getMe();
    if (me.role !== 'super_admin' && me.role !== 'support' && me.role !== 'compliance_officer') {
      apiLogout();
      throw new Error('Access denied: Super Panel is for platform operators only.');
    }
    setUser(me);
    return me;
  }, []);

  const logout = useCallback(() => {
    apiLogout();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
