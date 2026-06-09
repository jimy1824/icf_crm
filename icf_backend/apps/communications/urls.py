from django.urls import path
from .views import (
    CallLogViewSet,
    CallOutcomeView,
    CommunicationViewSet,
    ConsentViewSet,
    DeliverabilityWebhookView,
    MailboxConnectionViewSet,
    MeetingOutcomeView,
    MeetingViewSet,
    SuppressionViewSet,
    TriggerDomainViewSet,
)

urlpatterns = [
    # Mailbox OAuth (FM-07)
    path(
        "mailboxes/",
        MailboxConnectionViewSet.as_view({"get": "list", "post": "create"}),
        name="mailbox-list",
    ),
    # Trigger domains (BRU-02)
    path(
        "trigger-domains/",
        TriggerDomainViewSet.as_view({"get": "list", "post": "create"}),
        name="trigger-domain-list",
    ),
    # Communications timeline + advisor send (FM-10)
    path(
        "timeline/",
        CommunicationViewSet.as_view({"get": "list"}),
        name="communication-list",
    ),
    path(
        "send/",
        CommunicationViewSet.as_view({"post": "send"}),
        name="communication-send",
    ),
    # Call logs (FM-20)
    path(
        "calls/",
        CallLogViewSet.as_view({"get": "list", "post": "create"}),
        name="call-list",
    ),
    path(
        "calls/<int:pk>/outcome/",
        CallOutcomeView.as_view(),
        name="call-outcome",
    ),
    # Meetings (FM-19)
    path(
        "meetings/",
        MeetingViewSet.as_view({"get": "list", "post": "create"}),
        name="meeting-list",
    ),
    path(
        "meetings/<int:pk>/",
        MeetingViewSet.as_view({"get": "retrieve"}),
        name="meeting-detail",
    ),
    path(
        "meetings/<int:pk>/outcome/",
        MeetingOutcomeView.as_view(),
        name="meeting-outcome",
    ),
    # Suppression (FM-25)
    path(
        "suppression/",
        SuppressionViewSet.as_view({"get": "list", "post": "create"}),
        name="suppression-list",
    ),
    path(
        "suppression/<int:pk>/",
        SuppressionViewSet.as_view({"delete": "destroy"}),
        name="suppression-detail",
    ),
    # Consent (FM-24)
    path(
        "consent/",
        ConsentViewSet.as_view({"get": "list", "post": "create"}),
        name="consent-list",
    ),
    # Deliverability webhook (FM-25)
    path(
        "webhooks/deliverability/",
        DeliverabilityWebhookView.as_view(),
        name="deliverability-webhook",
    ),
]
