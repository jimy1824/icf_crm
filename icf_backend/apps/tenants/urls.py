from django.urls import path

from .views import (
    AssignPlanView,
    BillingDetailView,
    BillingListCreateView,
    CompanyLogoView,
    CompanyNotificationPreferencesView,
    CompanySettingsView,
    RecordPaymentView,
    StartTrialView,
    SubscriptionPlanListCreateView,
    TenantActivateView,
    TenantBrandingView,
    TenantDetailView,
    TenantDisableLoginView,
    TenantEnableLoginView,
    TenantExtendTrialView,
    TenantListCreateView,
    TenantSuspendView,
    TenantSubscriptionView,
    TenantUsageView,
)

urlpatterns = [
    # ---- Company self-service (tenant employees, own tenant only) ----
    path('company/settings/', CompanySettingsView.as_view(), name='company-settings'),
    path('company/logo/', CompanyLogoView.as_view(), name='company-logo'),
    path('company/notification-preferences/', CompanyNotificationPreferencesView.as_view(), name='company-notification-prefs'),

    # ---- Tenants ----
    path('', TenantListCreateView.as_view(), name='tenant-list'),
    path('<int:pk>/', TenantDetailView.as_view(), name='tenant-detail'),
    path('<int:pk>/suspend/', TenantSuspendView.as_view(), name='tenant-suspend'),
    path('<int:pk>/activate/', TenantActivateView.as_view(), name='tenant-activate'),
    path('<int:pk>/disable-login/', TenantDisableLoginView.as_view(), name='tenant-disable-login'),
    path('<int:pk>/enable-login/', TenantEnableLoginView.as_view(), name='tenant-enable-login'),
    path('<int:pk>/extend-trial/', TenantExtendTrialView.as_view(), name='tenant-extend-trial'),
    path('<int:pk>/usage/', TenantUsageView.as_view(), name='tenant-usage'),
    path('<int:pk>/branding/', TenantBrandingView.as_view(), name='tenant-branding'),

    # ---- Subscription plans ----
    path('plans/', SubscriptionPlanListCreateView.as_view(), name='plan-list'),

    # ---- Subscriptions ----
    path('subscriptions/<int:pk>/', TenantSubscriptionView.as_view(), name='subscription-detail'),
    path('subscriptions/<int:pk>/assign-plan/', AssignPlanView.as_view(), name='subscription-assign-plan'),
    path('subscriptions/<int:pk>/start-trial/', StartTrialView.as_view(), name='subscription-start-trial'),

    # ---- Billing ----
    path('billing/', BillingListCreateView.as_view(), name='billing-list'),
    path('billing/<int:pk>/', BillingDetailView.as_view(), name='billing-detail'),
    path('billing/<int:pk>/record-payment/', RecordPaymentView.as_view(), name='billing-record-payment'),
]
