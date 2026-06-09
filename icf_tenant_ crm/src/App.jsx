import { lazy, Suspense } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useParams } from 'react-router-dom';
import { useSelector } from 'react-redux';
import Shell from './components/layout/Shell.jsx';
import { PageSpinner } from './components/ui/Spinner.jsx';
import LoginPage from './pages/LoginPage.jsx';
import AccessDeniedPage from './pages/AccessDeniedPage.jsx';
import { useAuth } from './hooks/useAuth.js';
import { useNotificationPoller } from './hooks/useNotificationPoller.js';

// Lazy-loaded pages
const DashboardPage       = lazy(() => import('./pages/DashboardPage.jsx'));
const KanbanPage          = lazy(() => import('./pages/kanban/KanbanPage.jsx'));
const LeadListPage        = lazy(() => import('./pages/leads/LeadListPage.jsx'));
const PersonDetailPage    = lazy(() => import('./pages/leads/PersonDetailPage.jsx'));
const LeadCreatePage      = lazy(() => import('./pages/leads/LeadCreatePage.jsx'));
const LeadEditPage        = lazy(() => import('./pages/leads/LeadEditPage.jsx'));
const FinancialProfilePage= lazy(() => import('./pages/financials/FinancialProfilePage.jsx'));
const GoalsPage           = lazy(() => import('./pages/financials/GoalsPage.jsx'));
const DocumentsPage       = lazy(() => import('./pages/documents/DocumentsPage.jsx'));
const CampaignListPage    = lazy(() => import('./pages/campaigns/CampaignListPage.jsx'));
const CampaignDetailPage  = lazy(() => import('./pages/campaigns/CampaignDetailPage.jsx'));
const CommunicationsPage  = lazy(() => import('./pages/communications/CommunicationsPage.jsx'));
const CallsPage           = lazy(() => import('./pages/communications/CallsPage.jsx'));
const MeetingsPage        = lazy(() => import('./pages/communications/MeetingsPage.jsx'));
const CalculatorsPage     = lazy(() => import('./pages/calculators/CalculatorsPage.jsx'));
const AnalyticsDashboardPage = lazy(() => import('./pages/analytics/AnalyticsDashboardPage.jsx'));
const TerritoryListPage   = lazy(() => import('./pages/territories/TerritoryListPage.jsx'));
const TerritoryDetailPage = lazy(() => import('./pages/territories/TerritoryDetailPage.jsx'));
const UsersPage           = lazy(() => import('./pages/users/UsersPage.jsx'));
const NotificationsPage   = lazy(() => import('./pages/notifications/NotificationsPage.jsx'));
const SearchPage          = lazy(() => import('./pages/search/SearchPage.jsx'));

// Company Management pages
const CompanyOverviewPage       = lazy(() => import('./pages/company/CompanyOverviewPage.jsx'));
const CompanyEmployeesPage      = lazy(() => import('./pages/company/CompanyEmployeesPage.jsx'));
const CompanyTerritoriesPage    = lazy(() => import('./pages/company/CompanyTerritoriesPage.jsx'));
const CompanyPermissionsPage    = lazy(() => import('./pages/company/CompanyPermissionsPage.jsx'));
const CompanyBillingPage        = lazy(() => import('./pages/company/CompanyBillingPage.jsx'));
const CompanyTimeZonePage       = lazy(() => import('./pages/company/CompanyTimeZonePage.jsx'));
const CompanyNotificationsPage  = lazy(() => import('./pages/company/CompanyNotificationsPage.jsx'));
const CompanyBrandingPage       = lazy(() => import('./pages/company/CompanyBrandingPage.jsx'));
const CompanySupportPage        = lazy(() => import('./pages/company/CompanySupportPage.jsx'));

function RequireAuth({ children }) {
  const token = localStorage.getItem('crm_access_token');
  const user = useSelector((state) => state.auth.user);
  if (!token && !user) return <Navigate to="/login" replace />;
  return children;
}

function ClientRedirect() {
  const { id } = useParams();
  return <Navigate to={`/leads/${id}`} replace />;
}

function FirmAdminOnly({ children }) {
  const { isFirmAdmin, isTeamLead } = useAuth();
  if (!isFirmAdmin() && !isTeamLead()) return <AccessDeniedPage />;
  return children;
}

function AppShell() {
  useNotificationPoller();
  return (
    <RequireAuth>
      <Shell>
        <Suspense fallback={<PageSpinner />}>
          <Routes>
            <Route index element={<DashboardPage />} />
            <Route path="kanban" element={<KanbanPage />} />

            {/* Leads & Clients — single unified view */}
            <Route path="leads" element={<LeadListPage />} />
            <Route path="leads/new" element={<LeadCreatePage />} />
            <Route path="leads/:id" element={<PersonDetailPage />} />
            <Route path="leads/:id/edit" element={<LeadEditPage />} />
            <Route path="leads/:clientId/financial-profile" element={<FinancialProfilePage />} />
            <Route path="leads/:clientId/goals" element={<GoalsPage />} />
            <Route path="leads/:clientId/documents" element={<DocumentsPage />} />
            <Route path="leads/:clientId/communications" element={<CommunicationsPage />} />

            {/* Redirect legacy /clients/* URLs */}
            <Route path="clients" element={<Navigate to="/leads" replace />} />
            <Route path="clients/:id" element={<ClientRedirect />} />
            <Route path="clients/:id/*" element={<ClientRedirect />} />

            {/* Campaigns */}
            <Route path="campaigns" element={<CampaignListPage />} />
            <Route path="campaigns/:id" element={<CampaignDetailPage />} />

            {/* Communications */}
            <Route path="communications" element={<CommunicationsPage />} />
            <Route path="calls" element={<CallsPage />} />
            <Route path="meetings" element={<MeetingsPage />} />

            {/* Calculators */}
            <Route path="calculators" element={<CalculatorsPage />} />

            {/* Analytics */}
            <Route path="analytics" element={<AnalyticsDashboardPage />} />

            {/* Territories */}
            <Route path="territories" element={<TerritoryListPage />} />
            <Route path="territories/:id" element={<TerritoryDetailPage />} />

            {/* Admin */}
            <Route path="users" element={<FirmAdminOnly><UsersPage /></FirmAdminOnly>} />

            {/* Company Management (Tenant Admin + Team Lead) */}
            <Route path="company" element={<FirmAdminOnly><CompanyOverviewPage /></FirmAdminOnly>} />
            <Route path="company/employees" element={<FirmAdminOnly><CompanyEmployeesPage /></FirmAdminOnly>} />
            <Route path="company/territories" element={<FirmAdminOnly><CompanyTerritoriesPage /></FirmAdminOnly>} />
            <Route path="company/permissions" element={<FirmAdminOnly><CompanyPermissionsPage /></FirmAdminOnly>} />
            <Route path="company/billing" element={<FirmAdminOnly><CompanyBillingPage /></FirmAdminOnly>} />
            <Route path="company/timezone" element={<FirmAdminOnly><CompanyTimeZonePage /></FirmAdminOnly>} />
            <Route path="company/notifications" element={<FirmAdminOnly><CompanyNotificationsPage /></FirmAdminOnly>} />
            <Route path="company/branding" element={<FirmAdminOnly><CompanyBrandingPage /></FirmAdminOnly>} />
            <Route path="company/support" element={<FirmAdminOnly><CompanySupportPage /></FirmAdminOnly>} />

            {/* Misc */}
            <Route path="notifications" element={<NotificationsPage />} />
            <Route path="search" element={<SearchPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </Shell>
    </RequireAuth>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/access-denied" element={<AccessDeniedPage />} />
        <Route path="/*" element={<AppShell />} />
      </Routes>
    </BrowserRouter>
  );
}
