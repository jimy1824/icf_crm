from django.urls import path
from apps.leads.views import LeadViewSet

urlpatterns = [
    path(
        '',
        LeadViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='lead-list',
    ),
    path(
        'kanban/',
        LeadViewSet.as_view({'get': 'kanban'}),
        name='lead-kanban',
    ),
    path(
        '<int:pk>/',
        LeadViewSet.as_view({
            'get': 'retrieve',
            'put': 'update',
            'patch': 'partial_update',
            'delete': 'destroy',
        }),
        name='lead-detail',
    ),
    path(
        '<int:pk>/assign/',
        LeadViewSet.as_view({'post': 'assign'}),
        name='lead-assign',
    ),
    path(
        '<int:pk>/move-stage/',
        LeadViewSet.as_view({'post': 'move_stage'}),
        name='lead-move-stage',
    ),
    path(
        '<int:pk>/convert/',
        LeadViewSet.as_view({'post': 'convert'}),
        name='lead-convert',
    ),
    path(
        '<int:pk>/timeline/',
        LeadViewSet.as_view({'get': 'timeline', 'post': 'timeline'}),
        name='lead-timeline',
    ),
    path(
        '<int:pk>/opt-out/',
        LeadViewSet.as_view({'post': 'opt_out'}),
        name='lead-opt-out',
    ),
]
