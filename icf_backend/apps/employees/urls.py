from django.urls import path
from .views import EmployeeViewSet, RoleListView, PermissionListView

urlpatterns = [
    path('roles/', RoleListView.as_view(), name='role-list'),
    path('permissions/', PermissionListView.as_view(), name='permission-list'),
    path(
        '',
        EmployeeViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='employee-list',
    ),
    path(
        'me/',
        EmployeeViewSet.as_view({'get': 'me'}),
        name='employee-me',
    ),
    path(
        '<int:pk>/',
        EmployeeViewSet.as_view({'get': 'retrieve'}),
        name='employee-detail',
    ),
    path(
        '<int:pk>/assign-role/',
        EmployeeViewSet.as_view({'post': 'assign_role'}),
        name='employee-assign-role',
    ),
    path(
        '<int:pk>/deactivate/',
        EmployeeViewSet.as_view({'post': 'deactivate'}),
        name='employee-deactivate',
    ),
]
