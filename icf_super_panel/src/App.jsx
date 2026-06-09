import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext.jsx';
import { ThemeProvider } from './context/ThemeContext.jsx';
import ProtectedRoute from './router/ProtectedRoute.jsx';
import Shell from './components/layout/Shell.jsx';

import LoginPage from './pages/LoginPage.jsx';
import AccessDeniedPage from './pages/AccessDeniedPage.jsx';
import DashboardPage from './pages/DashboardPage.jsx';

import TenantListPage from './pages/tenants/TenantListPage.jsx';
import TenantCreatePage from './pages/tenants/TenantCreatePage.jsx';
import TenantDetailPage from './pages/tenants/TenantDetailPage.jsx';
import TenantEditPage from './pages/tenants/TenantEditPage.jsx';
import TenantSubscriptionPage from './pages/tenants/TenantSubscriptionPage.jsx';
import TenantBrandingPage from './pages/tenants/TenantBrandingPage.jsx';

import PlanListPage from './pages/plans/PlanListPage.jsx';

import BillingListPage from './pages/billing/BillingListPage.jsx';
import BillingDetailPage from './pages/billing/BillingDetailPage.jsx';

import SupportListPage from './pages/support/SupportListPage.jsx';
import SupportDetailPage from './pages/support/SupportDetailPage.jsx';
import EmployeesPage from './pages/employees/EmployeesPage.jsx';

import AuditLogPage from './pages/audit/AuditLogPage.jsx';
import AnalyticsDashboardPage from './pages/analytics/AnalyticsDashboardPage.jsx';

const OPERATOR_ROLES = ['super_admin', 'support', 'compliance_officer'];
const SUPER_ADMIN_ONLY = ['super_admin'];

function Guarded({ children, roles }) {
  return (
    <ProtectedRoute roles={roles ?? OPERATOR_ROLES}>
      {children}
    </ProtectedRoute>
  );
}

// Rendered inside AuthProvider — blocks rendering routes until auth resolves.
function AppRoutes() {
  const { loading } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
        <div className="w-8 h-8 rounded-full border-[3px] border-gray-200 dark:border-gray-700 border-t-brand-600 animate-spin" />
      </div>
    );
  }

  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/denied" element={<AccessDeniedPage />} />

      <Route
        path="/"
        element={
          <Guarded>
            <Shell />
          </Guarded>
        }
      >
        <Route index element={<DashboardPage />} />

        {/* FM-01: Tenants */}
        <Route path="tenants" element={<Guarded roles={['super_admin', 'support']}><TenantListPage /></Guarded>} />
        <Route path="tenants/new" element={<Guarded roles={SUPER_ADMIN_ONLY}><TenantCreatePage /></Guarded>} />
        <Route path="tenants/:id" element={<Guarded roles={['super_admin', 'support']}><TenantDetailPage /></Guarded>} />
        <Route path="tenants/:id/edit" element={<Guarded roles={SUPER_ADMIN_ONLY}><TenantEditPage /></Guarded>} />
        <Route path="tenants/:id/subscription" element={<Guarded roles={SUPER_ADMIN_ONLY}><TenantSubscriptionPage /></Guarded>} />
        <Route path="tenants/:id/branding" element={<Guarded roles={SUPER_ADMIN_ONLY}><TenantBrandingPage /></Guarded>} />

        {/* FM-02: Plans */}
        <Route path="plans" element={<Guarded roles={SUPER_ADMIN_ONLY}><PlanListPage /></Guarded>} />

        {/* FM-03: Billing */}
        <Route path="billing" element={<Guarded roles={SUPER_ADMIN_ONLY}><BillingListPage /></Guarded>} />
        <Route path="billing/:id" element={<Guarded roles={SUPER_ADMIN_ONLY}><BillingDetailPage /></Guarded>} />

        {/* FM-04: Support */}
        <Route path="support" element={<Guarded roles={['super_admin', 'support']}><SupportListPage /></Guarded>} />
        <Route path="support/:id" element={<Guarded roles={['super_admin', 'support']}><SupportDetailPage /></Guarded>} />

        {/* ICF Staff / Employees — Super Admin only */}
        <Route path="employees" element={<Guarded roles={SUPER_ADMIN_ONLY}><EmployeesPage /></Guarded>} />

        {/* FM-23/24: Audit */}
        <Route path="audit" element={<Guarded><AuditLogPage /></Guarded>} />

        {/* FM-12: Analytics */}
        <Route path="analytics" element={<Guarded roles={['super_admin', 'support']}><AnalyticsDashboardPage /></Guarded>} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <AppRoutes />
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
