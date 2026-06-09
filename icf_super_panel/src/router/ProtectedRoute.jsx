import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext.jsx';

export default function ProtectedRoute({ children, roles }) {
  const { user, loading } = useAuth();

  // AuthProvider shows full-screen spinner at app level while loading;
  // nested ProtectedRoute instances can safely return null here.
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/denied" replace />;

  return children;
}
