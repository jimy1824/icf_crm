from django.urls import path
from .views import (
    FirmDashboardView,
    AdvisorDashboardView,
    ClientDashboardView,
    PlatformDashboardView,
    AnalyticsSnapshotListView,
    TenantAdvisorsView,
    WeeklyLeadAnalyticsView,
    TodayLeadsView,
    TodayActivitiesView,
    TodayResponsesView,
    TerritoryLeadDistributionView,
)

urlpatterns = [
    # Existing dashboards
    path('dashboard/firm/', FirmDashboardView.as_view(), name='analytics-firm-dashboard'),
    path('dashboard/advisor/', AdvisorDashboardView.as_view(), name='analytics-advisor-dashboard'),
    path('dashboard/client/', ClientDashboardView.as_view(), name='analytics-client-dashboard'),
    path('dashboard/platform/', PlatformDashboardView.as_view(), name='analytics-platform-dashboard'),
    path('snapshots/', AnalyticsSnapshotListView.as_view(), name='analytics-snapshots'),
    # Advisor list (for filter dropdowns)
    path('advisors/', TenantAdvisorsView.as_view(), name='analytics-advisors'),
    # Dashboard Sections 1–5
    path('weekly-leads/', WeeklyLeadAnalyticsView.as_view(), name='analytics-weekly-leads'),
    path('today-leads/', TodayLeadsView.as_view(), name='analytics-today-leads'),
    path('today-activities/', TodayActivitiesView.as_view(), name='analytics-today-activities'),
    path('today-responses/', TodayResponsesView.as_view(), name='analytics-today-responses'),
    path('territory-distribution/', TerritoryLeadDistributionView.as_view(), name='analytics-territory-distribution'),
]
