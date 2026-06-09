from django.urls import path

from apps.campaign_timeline.views import (
    AdvisorTimelineView,
    CampaignTimelineView,
    EnrollmentTimelineView,
    LeadTimelineView,
    TimelineDashboardView,
)

urlpatterns = [
    path('leads/<int:lead_id>/', LeadTimelineView.as_view(), name='timeline-lead'),
    path('campaigns/<int:campaign_id>/', CampaignTimelineView.as_view(), name='timeline-campaign'),
    path('enrollments/<int:enrollment_id>/', EnrollmentTimelineView.as_view(), name='timeline-enrollment'),
    path('advisor/', AdvisorTimelineView.as_view(), name='timeline-advisor'),
    path('dashboard/', TimelineDashboardView.as_view(), name='timeline-dashboard'),
]
