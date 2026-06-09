from django.contrib import admin
from django.urls import path, include

from apps.users.auth_views import (
    AuthMeView,
    ChangePasswordView,
    CustomerPortalLoginView,
    MFAStatusView,
    SuperPanelLoginView,
    TenantCRMLoginView,
    TokenRefreshView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # FM-06: Three-platform authentication (Authentication Matrix — CLAUDE.md)
    # Each endpoint enforces user_type — cross-platform login is impossible.
    path('api/v1/auth/super/token/', SuperPanelLoginView.as_view(), name='super-token'),
    path('api/v1/auth/crm/token/', TenantCRMLoginView.as_view(), name='crm-token'),
    path('api/v1/auth/portal/token/', CustomerPortalLoginView.as_view(), name='portal-token'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/v1/auth/me/', AuthMeView.as_view(), name='auth-me'),
    path('api/v1/auth/change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
    path('api/v1/auth/mfa/', MFAStatusView.as_view(), name='auth-mfa'),

    # Tenant-scoped resources
    path('api/v1/tenants/', include('apps.tenants.urls')),
    path('api/v1/users/', include('apps.users.urls')),
    path('api/v1/leads/', include('apps.leads.urls')),
    path('api/v1/employees/', include('apps.employees.urls')),
    # FM-15/16/21: Financial profile, goals, calculators — nested under financials/
    path('api/v1/financials/', include('apps.financials.urls')),
    path('api/v1/campaigns/', include('apps.campaigns.urls')),
    path('api/v1/communications/', include('apps.communications.urls')),
    # FM-11: Documents + KYC — nested under documents/
    path('api/v1/documents/', include('apps.documents.urls')),
    path('api/v1/notifications/', include('apps.notifications.urls')),

    # Compliance & audit
    path('api/v1/audit/', include('apps.audit.urls')),

    # FM-22: Global search (BRU-35)
    path('api/v1/search/', include('apps.search.urls')),

    # FM-12/26: Analytics dashboards
    path('api/v1/analytics/', include('apps.analytics.urls')),

    # FM-04: Support ticketing
    path('api/v1/support/', include('apps.support.urls')),

    # BRU-36/37/38: Compliance — retention, legal holds, supervision
    path('api/v1/compliance/', include('apps.compliance.urls')),

    # Territory management — lead distribution, campaign targeting, analytics
    path('api/v1/territories/', include('apps.territories.urls')),

    # Timezone configuration — tenant office hours, advisor TZ overrides
    path('api/v1/timezones/', include('apps.timezones.urls')),

    # Campaign Execution Timeline — schedule, dashboard, analytics
    path('api/v1/timeline/', include('apps.campaign_timeline.urls')),

    # Customer Portal (FM-?? / Authentication Matrix — customers only)
    path('api/v1/portal/', include('apps.portal.urls')),
]
