from django.urls import path
from .views import (
    SupportTicketListView,
    SupportTicketDetailView,
    TicketStatusView,
    TicketAssignView,
    TicketCommentListView,
    TicketStatsView,
    TicketUpdateView,
    SupportStaffListView,
    PlatformStaffListView,
    PlatformStaffDetailView,
    PlatformStaffDeactivateView,
    PlatformStaffStatsView,
)

urlpatterns = [
    # Fixed paths before parameterised ones to avoid URL conflicts
    path('tickets/stats/', TicketStatsView.as_view(), name='ticket-stats'),
    path('staff/', SupportStaffListView.as_view(), name='support-staff-list'),
    path('tickets/', SupportTicketListView.as_view(), name='ticket-list'),
    path('tickets/<int:pk>/', SupportTicketDetailView.as_view(), name='ticket-detail'),
    path('tickets/<int:pk>/status/', TicketStatusView.as_view(), name='ticket-status'),
    path('tickets/<int:pk>/update/', TicketUpdateView.as_view(), name='ticket-update'),
    path('tickets/<int:pk>/assign/', TicketAssignView.as_view(), name='ticket-assign'),
    path('tickets/<int:pk>/comments/', TicketCommentListView.as_view(), name='ticket-comments'),

    # Platform staff management (Super Admin only)
    path('platform-staff/stats/', PlatformStaffStatsView.as_view(), name='platform-staff-stats'),
    path('platform-staff/', PlatformStaffListView.as_view(), name='platform-staff-list'),
    path('platform-staff/<int:pk>/', PlatformStaffDetailView.as_view(), name='platform-staff-detail'),
    path('platform-staff/<int:pk>/deactivate/', PlatformStaffDeactivateView.as_view(), {'action_type': 'deactivate'}, name='platform-staff-deactivate'),
    path('platform-staff/<int:pk>/activate/', PlatformStaffDeactivateView.as_view(), {'action_type': 'activate'}, name='platform-staff-activate'),
]
