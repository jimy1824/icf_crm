from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsSuperAdmin, IsTenantAdmin
from apps.tenants.models import BillingRecord, SubscriptionPlan, Tenant, TenantSubscription
from apps.tenants.serializers import (
    BillingRecordCreateSerializer,
    BillingRecordSerializer,
    CompanySettingsSerializer,
    CompanySettingsUpdateSerializer,
    ExtendTrialSerializer,
    LogoUrlUpdateSerializer,
    NotificationPreferenceBulkUpdateSerializer,
    NotificationPreferenceSerializer,
    RecordPaymentSerializer,
    SubscriptionPlanCreateSerializer,
    SubscriptionPlanSerializer,
    TenantBrandingSerializer,
    TenantBrandingUpdateSerializer,
    TenantCreateSerializer,
    TenantProfileUpdateSerializer,
    TenantSerializer,
    TenantSubscriptionSerializer,
    TenantUsageSerializer,
)
from apps.tenants.services import (
    BillingService,
    BrandingService,
    SubscriptionService,
    activate_tenant,
    create_tenant,
    disable_login,
    enable_login,
    suspend_tenant,
    update_tenant_profile,
)


def _drf(exc: DjangoValidationError) -> DRFValidationError:
    msgs = list(exc.messages) if hasattr(exc, 'messages') else [str(exc)]
    return DRFValidationError(detail=msgs)


def _get_tenant_or_404(pk):
    try:
        return Tenant.objects.get(pk=pk)
    except Tenant.DoesNotExist:
        raise NotFound("Tenant not found.")


# ---------------------------------------------------------------------------
# Tenant list / create
# ---------------------------------------------------------------------------

class TenantListCreateView(APIView):
    """
    GET  /tenants/          — Super Admin: list all tenants with usage
    POST /tenants/          — Super Admin: provision new tenant
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSuperAdmin()]

    def get(self, request):
        user = request.user
        if user.role == 'super_admin':
            qs = Tenant.objects.select_related('subscription__plan').all()
        elif user.tenant_id:
            qs = Tenant.objects.filter(pk=user.tenant_id).select_related('subscription__plan')
        else:
            qs = Tenant.objects.none()
        return Response(TenantSerializer(qs, many=True).data)

    def post(self, request):
        serializer = TenantCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        try:
            tenant = create_tenant(
                firm_name=d['firm_name'],
                legal_name=d.get('legal_name', ''),
                website=d.get('website', ''),
                company_email=d.get('company_email', ''),
                phone=d.get('phone', ''),
                address_line1=d.get('address_line1', ''),
                city=d.get('city', ''),
                state=d.get('state', ''),
                country=d.get('country', 'US'),
                postal_code=d.get('postal_code', ''),
                region=d.get('region', ''),
                timezone_name=d.get('timezone', 'America/New_York'),
                plan_id=d['plan_id'],
                is_trial=d.get('is_trial', False),
                trial_days=d.get('trial_days', 14),
                actor=request.user,
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(TenantSerializer(tenant).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Tenant detail / update
# ---------------------------------------------------------------------------

class TenantDetailView(APIView):
    """
    GET   /tenants/<id>/   — Super Admin or own Tenant Admin
    PATCH /tenants/<id>/   — Super Admin only
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def _check_access(self, request, tenant):
        user = request.user
        if user.role == 'super_admin':
            return
        if user.tenant_id == tenant.pk:
            return
        raise DRFValidationError("BRU-01: Access denied.")

    def get(self, request, pk=None):
        tenant = _get_tenant_or_404(pk)
        self._check_access(request, tenant)
        return Response(TenantSerializer(tenant).data)

    def patch(self, request, pk=None):
        if request.user.role != 'super_admin':
            # Tenant admins can update their own profile
            if request.user.role != 'tenant_admin' or request.user.tenant_id != int(pk):
                raise DRFValidationError("Only Super Admin or own Tenant Admin can update.")
        tenant = _get_tenant_or_404(pk)
        serializer = TenantProfileUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            tenant = update_tenant_profile(
                tenant=tenant, actor=request.user,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(TenantSerializer(tenant).data)


# ---------------------------------------------------------------------------
# Tenant lifecycle actions
# ---------------------------------------------------------------------------

class TenantSuspendView(APIView):
    """POST /tenants/<id>/suspend/ — Super Admin"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk=None):
        tenant = _get_tenant_or_404(pk)
        suspend_tenant(tenant=tenant, actor=request.user)
        return Response(TenantSerializer(tenant).data)


class TenantActivateView(APIView):
    """POST /tenants/<id>/activate/ — Super Admin"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk=None):
        tenant = _get_tenant_or_404(pk)
        activate_tenant(tenant=tenant, actor=request.user)
        return Response(TenantSerializer(tenant).data)


class TenantDisableLoginView(APIView):
    """POST /tenants/<id>/disable-login/ — Super Admin"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk=None):
        tenant = _get_tenant_or_404(pk)
        disable_login(tenant=tenant, actor=request.user)
        return Response({'login_disabled': True})


class TenantEnableLoginView(APIView):
    """POST /tenants/<id>/enable-login/ — Super Admin"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk=None):
        tenant = _get_tenant_or_404(pk)
        enable_login(tenant=tenant, actor=request.user)
        return Response({'login_disabled': False})


class TenantExtendTrialView(APIView):
    """POST /tenants/<id>/extend-trial/ — Super Admin"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk=None):
        tenant = _get_tenant_or_404(pk)
        serializer = ExtendTrialSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            sub = SubscriptionService.extend_trial(
                tenant=tenant,
                days=serializer.validated_data['days'],
                actor=request.user,
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(TenantSubscriptionSerializer(sub).data)


class TenantUsageView(APIView):
    """GET /tenants/<id>/usage/ — Super Admin or own Tenant Admin"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        tenant = _get_tenant_or_404(pk)
        user = request.user
        if user.role not in ('super_admin',) and user.tenant_id != tenant.pk:
            raise DRFValidationError("BRU-01: Access denied.")
        data = SubscriptionService.get_usage_summary(tenant=tenant)
        serializer = TenantUsageSerializer(data=data)
        serializer.is_valid()
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Branding
# ---------------------------------------------------------------------------

class TenantBrandingView(APIView):
    """
    GET   /tenants/<id>/branding/
    PATCH /tenants/<id>/branding/
    Tenant Admin+
    """
    permission_classes = [IsAuthenticated]

    def _check(self, request, pk):
        user = request.user
        if user.role == 'super_admin':
            return _get_tenant_or_404(pk)
        if user.role == 'tenant_admin' and user.tenant_id == int(pk):
            return _get_tenant_or_404(pk)
        raise DRFValidationError("BRU-01: Access denied.")

    def get(self, request, pk=None):
        tenant = self._check(request, pk)
        branding = BrandingService.get_or_create(tenant)
        return Response(TenantBrandingSerializer(branding).data)

    def patch(self, request, pk=None):
        tenant = self._check(request, pk)
        serializer = TenantBrandingUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        branding = BrandingService.update(
            tenant=tenant, actor=request.user, **serializer.validated_data,
        )
        return Response(TenantBrandingSerializer(branding).data)


# ---------------------------------------------------------------------------
# Subscription plans (Super Admin CRUD)
# ---------------------------------------------------------------------------

class SubscriptionPlanListCreateView(APIView):
    """
    GET  /plans/   — All authenticated
    POST /plans/   — Super Admin
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSuperAdmin()]

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True)
        return Response(SubscriptionPlanSerializer(plans, many=True).data)

    def post(self, request):
        serializer = SubscriptionPlanCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        plan = SubscriptionPlan.objects.create(
            name=d['name'],
            max_leads=d['max_leads'],
            max_users=d['max_users'],
            max_storage_gb=d['max_storage_gb'],
            max_campaigns=d.get('max_campaigns', 0),
            features=d.get('features', {}),
        )
        return Response(SubscriptionPlanSerializer(plan).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Subscriptions
# ---------------------------------------------------------------------------

class TenantSubscriptionView(APIView):
    """GET /subscriptions/<id>/ — Super Admin or own Tenant Admin"""
    permission_classes = [IsAuthenticated]

    def get(self, request, pk=None):
        try:
            sub = TenantSubscription.objects.select_related('plan', 'tenant').get(pk=pk)
        except TenantSubscription.DoesNotExist:
            raise NotFound("Subscription not found.")
        user = request.user
        if user.role not in ('super_admin',) and user.tenant_id != sub.tenant_id:
            raise DRFValidationError("BRU-01: Access denied.")
        return Response(TenantSubscriptionSerializer(sub).data)


class AssignPlanView(APIView):
    """POST /subscriptions/<id>/assign-plan/ — Super Admin"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk=None):
        try:
            sub = TenantSubscription.objects.select_related('plan', 'tenant').get(pk=pk)
        except TenantSubscription.DoesNotExist:
            raise NotFound("Subscription not found.")
        plan_id = request.data.get('plan_id')
        if not plan_id:
            raise DRFValidationError({'plan_id': 'Required.'})
        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id)
        except SubscriptionPlan.DoesNotExist:
            raise NotFound("Plan not found.")
        try:
            sub = SubscriptionService.assign_plan(
                tenant=sub.tenant, plan=plan, actor=request.user,
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(TenantSubscriptionSerializer(sub).data)


class StartTrialView(APIView):
    """POST /subscriptions/<id>/start-trial/ — Super Admin"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk=None):
        try:
            sub = TenantSubscription.objects.select_related('plan', 'tenant').get(pk=pk)
        except TenantSubscription.DoesNotExist:
            raise NotFound("Subscription not found.")
        plan_id = request.data.get('plan_id')
        trial_days = int(request.data.get('trial_days', 14))
        plan = sub.plan
        if plan_id:
            try:
                plan = SubscriptionPlan.objects.get(pk=plan_id)
            except SubscriptionPlan.DoesNotExist:
                raise NotFound("Plan not found.")
        sub = SubscriptionService.start_trial(
            tenant=sub.tenant, plan=plan, trial_days=trial_days, actor=request.user,
        )
        return Response(TenantSubscriptionSerializer(sub).data)


# ---------------------------------------------------------------------------
# Billing
# ---------------------------------------------------------------------------

class BillingListCreateView(APIView):
    """
    GET  /billing/?tenant_id=   — Super Admin or Billing Manager (own tenant)
    POST /billing/              — Super Admin
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAuthenticated(), IsTenantAdmin()]
        return [IsAuthenticated(), IsSuperAdmin()]

    def get(self, request):
        user = request.user
        tenant_id = request.query_params.get('tenant_id')
        if user.role == 'super_admin':
            qs = BillingRecord.objects.all()
            if tenant_id:
                qs = qs.filter(tenant_id=tenant_id)
        else:
            qs = BillingRecord.objects.filter(tenant_id=user.tenant_id)
        return Response(BillingRecordSerializer(qs.order_by('-created_at'), many=True).data)

    def post(self, request):
        serializer = BillingRecordCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        tenant_id = request.data.get('tenant_id')
        if not tenant_id:
            raise DRFValidationError({'tenant_id': 'Required.'})
        tenant = _get_tenant_or_404(tenant_id)
        record = BillingService.record_invoice(
            tenant=tenant,
            amount_cents=d['amount_cents'],
            currency=d['currency'],
            period_start=d['period_start'],
            period_end=d['period_end'],
            external_invoice_id=d.get('external_invoice_id', ''),
            invoice_number=d.get('invoice_number', ''),
            tax_amount_cents=d.get('tax_amount_cents', 0),
            discount_amount_cents=d.get('discount_amount_cents', 0),
            actor=request.user,
        )
        return Response(BillingRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class BillingDetailView(APIView):
    """GET /billing/<id>/ — Super Admin or own Billing Manager"""
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get(self, request, pk=None):
        try:
            record = BillingRecord.objects.get(pk=pk)
        except BillingRecord.DoesNotExist:
            raise NotFound("Billing record not found.")
        user = request.user
        if user.role not in ('super_admin',) and user.tenant_id != record.tenant_id:
            raise DRFValidationError("BRU-01: Access denied.")
        return Response(BillingRecordSerializer(record).data)


class RecordPaymentView(APIView):
    """POST /billing/<id>/record-payment/ — Super Admin"""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def post(self, request, pk=None):
        try:
            record = BillingRecord.objects.select_related('tenant').get(pk=pk)
        except BillingRecord.DoesNotExist:
            raise NotFound("Billing record not found.")
        serializer = RecordPaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = BillingService.record_payment(
            tenant=record.tenant,
            billing_record=record,
            payment_method=serializer.validated_data.get('payment_method', ''),
            transaction_id=serializer.validated_data.get('transaction_id', ''),
            actor=request.user,
        )
        return Response(BillingRecordSerializer(record).data)


# ---------------------------------------------------------------------------
# Company-facing endpoints (tenant employees accessing their own firm data)
# ---------------------------------------------------------------------------

class CompanySettingsView(APIView):
    """
    GET   /tenants/company/settings/  — return own tenant profile
    PATCH /tenants/company/settings/  — update own tenant profile (Tenant Admin only)
    BRU-01: always scoped to request.user.tenant.
    """

    def get_permissions(self):
        return [IsAuthenticated()]

    def _require_tenant(self, request):
        if not request.user.tenant_id:
            raise DRFValidationError("No tenant associated with this account.")
        return request.user.tenant

    def get(self, request):
        tenant = self._require_tenant(request)
        tenant = Tenant.objects.select_related('subscription__plan').get(pk=tenant.pk)
        return Response(CompanySettingsSerializer(tenant).data)

    def patch(self, request):
        tenant = self._require_tenant(request)
        if request.user.role not in ('tenant_admin', 'firm_admin'):
            raise DRFValidationError("Only Tenant Admin can update company settings.")
        serializer = CompanySettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            tenant = update_tenant_profile(
                tenant=tenant,
                actor=request.user,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        tenant = Tenant.objects.select_related('subscription__plan').get(pk=tenant.pk)
        return Response(CompanySettingsSerializer(tenant).data)


class CompanyLogoView(APIView):
    """
    PATCH /tenants/company/logo/  — update logo_url (Tenant Admin only).
    Accepts a pre-signed/uploaded URL; file upload itself is handled by the client
    directly against object storage (S3/GCS). Backend stores the resulting URL.
    BRU-01: scoped to request.user.tenant.
    """
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def patch(self, request):
        if not request.user.tenant_id:
            raise DRFValidationError("No tenant associated with this account.")
        serializer = LogoUrlUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tenant = request.user.tenant
        try:
            tenant = update_tenant_profile(
                tenant=tenant,
                actor=request.user,
                logo_url=serializer.validated_data['logo_url'],
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response({'logo_url': tenant.logo_url})


class CompanyNotificationPreferencesView(APIView):
    """
    GET   /tenants/company/notification-preferences/  — list own preferences
    PUT   /tenants/company/notification-preferences/  — bulk upsert preferences
    BRU-01: preferences scoped to the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.tenants.models import NotificationPreference
        prefs = NotificationPreference.objects.filter(user=request.user).order_by('event_type')
        return Response(NotificationPreferenceSerializer(prefs, many=True).data)

    def put(self, request):
        from apps.tenants.services import NotificationPreferenceService
        serializer = NotificationPreferenceBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        results = []
        for item in serializer.validated_data['preferences']:
            event_type = item.pop('event_type')
            pref = NotificationPreferenceService.update_preference(
                user=request.user,
                event_type=event_type,
                **item,
            )
            results.append(pref)
        return Response(NotificationPreferenceSerializer(results, many=True).data)
