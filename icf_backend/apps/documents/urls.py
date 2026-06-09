from django.urls import path

from .views import DocumentKYCView, DocumentViewSet, PendingKYCViewSet

urlpatterns = [
    # FM-11: documents nested under /documents/leads/{lead_pk}/
    path(
        "leads/<int:lead_pk>/documents/",
        DocumentViewSet.as_view({"get": "list", "post": "create"}),
        name="document-list",
    ),
    path(
        "leads/<int:lead_pk>/documents/<int:pk>/",
        DocumentViewSet.as_view({"get": "retrieve", "delete": "destroy"}),
        name="document-detail",
    ),

    # BRU-30: KYC lifecycle — compliance officers only
    path(
        "leads/<int:lead_pk>/documents/<int:pk>/verify/",
        DocumentKYCView.as_view(),
        {"action_name": "verify"},
        name="document-verify",
    ),
    path(
        "leads/<int:lead_pk>/documents/<int:pk>/reject/",
        DocumentKYCView.as_view(),
        {"action_name": "reject"},
        name="document-reject",
    ),
    path(
        "leads/<int:lead_pk>/documents/<int:pk>/legal-hold/",
        DocumentKYCView.as_view(),
        {"action_name": "legal-hold"},
        name="document-legal-hold",
    ),

    # Compliance queue (KYC pending)
    path(
        "documents/kyc-pending/",
        PendingKYCViewSet.as_view({"get": "list"}),
        name="document-kyc-pending",
    ),
]
