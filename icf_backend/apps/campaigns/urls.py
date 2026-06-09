from django.urls import path
from .views import (
    CampaignActivateView,
    CampaignEnrollmentStopView,
    CampaignEnrollViewSet,
    CampaignPauseView,
    CampaignViewSet,
)

urlpatterns = [
    path("", CampaignViewSet.as_view({"get": "list", "post": "create"}), name="campaign-list"),
    path("<int:pk>/", CampaignViewSet.as_view({"get": "retrieve"}), name="campaign-detail"),
    path(
        "<int:pk>/activate/",
        CampaignActivateView.as_view({"post": "create"}),
        name="campaign-activate",
    ),
    path(
        "<int:pk>/pause/",
        CampaignPauseView.as_view({"post": "create"}),
        name="campaign-pause",
    ),
    path(
        "<int:campaign_pk>/enrollments/",
        CampaignEnrollViewSet.as_view({"get": "list", "post": "create"}),
        name="campaign-enrollment-list",
    ),
    path(
        "enrollments/<int:enrollment_pk>/stop/",
        CampaignEnrollmentStopView.as_view({"post": "create"}),
        name="campaign-enrollment-stop",
    ),
]
