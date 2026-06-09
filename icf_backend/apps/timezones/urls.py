from django.urls import path

from apps.timezones.views import AdvisorTimeZoneView, TenantTimeZoneView

urlpatterns = [
    path('tenant/', TenantTimeZoneView.as_view(), name='timezone-tenant'),
    path('advisor/', AdvisorTimeZoneView.as_view(), name='timezone-advisor'),
]
