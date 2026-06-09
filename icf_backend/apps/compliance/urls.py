from django.urls import path
from .views import (
    RetentionPolicyView,
    RetentionRecordListView,
    LegalHoldPlaceView,
    LegalHoldLiftView,
    SupervisionReviewListView,
    SupervisionReviewApproveView,
    SupervisionReviewRejectView,
    SupervisionReviewEscalateView,
)

urlpatterns = [
    # BRU-37: Retention policies
    path('retention/policies/', RetentionPolicyView.as_view(), name='retention-policy'),
    path('retention/records/', RetentionRecordListView.as_view(), name='retention-records'),

    # BRU-38: Legal holds
    path('legal-hold/', LegalHoldPlaceView.as_view(), name='legal-hold-place'),
    path(
        'legal-hold/<str:entity_type>/<str:entity_id>/lift/',
        LegalHoldLiftView.as_view(), name='legal-hold-lift',
    ),

    # BRU-36: Supervision review queue
    path('supervision/reviews/', SupervisionReviewListView.as_view(), name='supervision-reviews'),
    path(
        'supervision/reviews/<int:pk>/approve/',
        SupervisionReviewApproveView.as_view(), name='supervision-approve',
    ),
    path(
        'supervision/reviews/<int:pk>/reject/',
        SupervisionReviewRejectView.as_view(), name='supervision-reject',
    ),
    path(
        'supervision/reviews/<int:pk>/escalate/',
        SupervisionReviewEscalateView.as_view(), name='supervision-escalate',
    ),
]
