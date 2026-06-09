from django.urls import path
from .views import UserViewSet

urlpatterns = [
    path(
        "",
        UserViewSet.as_view({"get": "list", "post": "create"}),
        name="user-list",
    ),
    path(
        "me/",
        UserViewSet.as_view({"get": "me"}),
        name="user-me",
    ),
    path(
        "<int:pk>/",
        UserViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "patch": "partial_update",
            "delete": "destroy",
        }),
        name="user-detail",
    ),
    path(
        "<int:pk>/deactivate/",
        UserViewSet.as_view({"post": "deactivate"}),
        name="user-deactivate",
    ),
]
