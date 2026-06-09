from django.urls import path
from .views import (
    TerritoryListCreateView,
    TerritoryDetailView,
    TerritoryAdvisorsView,
    TerritoryAdvisorRemoveView,
    AdvisorTerritoriesView,
    TerritorySummaryView,
    TerritoryWeeklyView,
    AdvisorTerritoryAnalyticsView,
    TerritoryGraphLeadsView,
    TerritoryGraphAdvisorsView,
    TerritoryGraphWeeklyTrendView,
    TerritoryGraphCampaignsView,
    TerritoryGraphConversionView,
)

urlpatterns = [
    # Territory CRUD
    path('', TerritoryListCreateView.as_view(), name='territory-list'),
    path('<int:pk>/', TerritoryDetailView.as_view(), name='territory-detail'),

    # Advisor assignment
    path('<int:pk>/advisors/', TerritoryAdvisorsView.as_view(), name='territory-advisors'),
    path('<int:pk>/assign-advisor/', TerritoryAdvisorsView.as_view(), name='territory-assign-advisor'),
    path('<int:pk>/advisors/<int:advisor_pk>/', TerritoryAdvisorRemoveView.as_view(), name='territory-remove-advisor'),
    path('advisor/<int:advisor_pk>/', AdvisorTerritoriesView.as_view(), name='advisor-territories'),

    # Per-territory analytics
    path('<int:pk>/analytics/summary/', TerritorySummaryView.as_view(), name='territory-analytics-summary'),
    path('<int:pk>/analytics/weekly/', TerritoryWeeklyView.as_view(), name='territory-analytics-weekly'),

    # Cross-territory analytics
    path('analytics/advisor/<int:advisor_pk>/', AdvisorTerritoryAnalyticsView.as_view(), name='territory-analytics-advisor'),

    # Graph / chart data
    path('analytics/graph/leads/', TerritoryGraphLeadsView.as_view(), name='territory-graph-leads'),
    path('analytics/graph/advisors/', TerritoryGraphAdvisorsView.as_view(), name='territory-graph-advisors'),
    path('analytics/graph/weekly-trend/', TerritoryGraphWeeklyTrendView.as_view(), name='territory-graph-weekly-trend'),
    path('analytics/graph/campaigns/', TerritoryGraphCampaignsView.as_view(), name='territory-graph-campaigns'),
    path('analytics/graph/conversion/', TerritoryGraphConversionView.as_view(), name='territory-graph-conversion'),
]
