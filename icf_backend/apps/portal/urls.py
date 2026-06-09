from django.urls import path
from apps.portal.views import (
    PortalAdvisorListView,
    PortalConsentView,
    PortalDashboardView,
    PortalDocumentDetailView,
    PortalDocumentListView,
    PortalFinancialSummaryView,
    PortalGoalDetailView,
    PortalGoalListView,
    PortalHouseholdView,
    PortalMeView,
    PortalMeetingListView,
    PortalMeetingRSVPView,
    PortalMessageListView,
    PortalNotificationListView,
    PortalNotificationReadAllView,
    PortalNotificationReadView,
    PortalNotificationUnreadCountView,
)

urlpatterns = [
    # Profile
    path('me/', PortalMeView.as_view(), name='portal-me'),

    # Financial
    path('financial-summary/', PortalFinancialSummaryView.as_view(), name='portal-financial-summary'),

    # Goals
    path('goals/', PortalGoalListView.as_view(), name='portal-goal-list'),
    path('goals/<int:pk>/', PortalGoalDetailView.as_view(), name='portal-goal-detail'),

    # Documents
    path('documents/', PortalDocumentListView.as_view(), name='portal-document-list'),
    path('documents/<int:pk>/', PortalDocumentDetailView.as_view(), name='portal-document-detail'),

    # Meetings
    path('meetings/', PortalMeetingListView.as_view(), name='portal-meeting-list'),
    path('meetings/<int:pk>/rsvp/', PortalMeetingRSVPView.as_view(), name='portal-meeting-rsvp'),

    # Messages (communications)
    path('messages/', PortalMessageListView.as_view(), name='portal-message-list'),

    # Notifications
    path('notifications/', PortalNotificationListView.as_view(), name='portal-notification-list'),
    path('notifications/unread-count/', PortalNotificationUnreadCountView.as_view(), name='portal-notification-unread-count'),
    path('notifications/read-all/', PortalNotificationReadAllView.as_view(), name='portal-notification-read-all'),
    path('notifications/<int:pk>/read/', PortalNotificationReadView.as_view(), name='portal-notification-read'),

    # Advisors
    path('advisors/', PortalAdvisorListView.as_view(), name='portal-advisor-list'),

    # Consent
    path('consent/', PortalConsentView.as_view(), name='portal-consent'),

    # Household (BRU-28)
    path('household/', PortalHouseholdView.as_view(), name='portal-household'),

    # Dashboard
    path('dashboard/', PortalDashboardView.as_view(), name='portal-dashboard'),
]
