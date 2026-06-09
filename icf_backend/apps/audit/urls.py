from django.urls import path
from .views import AuditEventViewSet

urlpatterns = [
    path(
        "events/",
        AuditEventViewSet.as_view({"get": "list"}),
        name="audit-event-list",
    ),
    path(
        "events/<int:pk>/",
        AuditEventViewSet.as_view({"get": "retrieve"}),
        name="audit-event-detail",
    ),
]
