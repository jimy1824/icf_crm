from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView as _BaseTokenRefreshView

from apps.audit.services import AuditService
from apps.users.models import CustomUser, CustomerAccount
from apps.users.serializers import ChangePasswordSerializer, MFAStatusSerializer, UserSerializer


# ---------------------------------------------------------------------------
# Three-platform authentication endpoints (Authentication Matrix — CLAUDE.md)
# ---------------------------------------------------------------------------

class SuperPanelLoginView(TokenObtainPairView):
    """
    POST /api/v1/auth/super/token/
    Super Panel login — platform staff only (Super Admin, Support, Compliance Officer).
    Users with user_type != 'platform_staff' are REJECTED even if credentials are valid.
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            # Validate user_type after successful credential check
            from rest_framework_simplejwt.tokens import AccessToken
            token = AccessToken(response.data['access'])
            user_id = token['user_id']
            user = CustomUser.objects.get(pk=user_id)
            if user.user_type != CustomUser.TYPE_PLATFORM_STAFF:
                raise AuthenticationFailed(
                    "This login endpoint is for platform staff only."
                )
        return response


class TenantCRMLoginView(TokenObtainPairView):
    """
    POST /api/v1/auth/crm/token/
    Tenant CRM login — tenant employees only (Tenant Admin, Team Lead, Advisor).
    Users with user_type != 'tenant_employee' are REJECTED even if credentials are valid.
    """

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        if response.status_code == 200:
            from rest_framework_simplejwt.tokens import AccessToken
            token = AccessToken(response.data['access'])
            user_id = token['user_id']
            user = CustomUser.objects.get(pk=user_id)
            if user.user_type != CustomUser.TYPE_TENANT_EMPLOYEE:
                raise AuthenticationFailed(
                    "This login endpoint is for tenant employees only."
                )
        return response


class CustomerPortalLoginView(APIView):
    """
    POST /api/v1/auth/portal/token/
    Customer Portal login — leads/clients only.
    Authenticates against CustomerAccount, never CustomUser.
    Rejects with 403 if the email belongs to a CustomUser (platform staff / tenant employee).
    Response: { "access": "...", "refresh": "...", "lead_id": "...", "lead_status": "...", "user_type": "customer" }
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        email = request.data.get('email', '').strip().lower()
        password = request.data.get('password', '')

        if not email or not password:
            return Response(
                {'detail': 'Email and password are required.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # BRU: Platform staff and tenant employees may NEVER log in via the portal
        if CustomUser.objects.filter(email__iexact=email).exists():
            return Response(
                {'detail': 'This login endpoint is for customer portal users only.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            account = CustomerAccount.objects.select_related('lead', 'tenant').get(
                email__iexact=email,
                is_active=True,
            )
        except CustomerAccount.DoesNotExist:
            return Response(
                {'detail': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not account.lead.portal_enabled:
            return Response(
                {'detail': 'Portal access is not enabled for this account.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        if not account.check_password(password):
            return Response(
                {'detail': 'Invalid email or password.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # Issue portal-scoped JWT tokens with custom claims
        refresh = RefreshToken()
        refresh['user_type'] = 'customer'
        refresh['customer_id'] = account.pk
        refresh['tenant_id'] = account.tenant_id

        access = refresh.access_token
        access['user_type'] = 'customer'
        access['customer_id'] = account.pk
        access['tenant_id'] = account.tenant_id

        # Update last_login (BRU-33 audit via login action)
        account.last_login = timezone.now()
        account.save(update_fields=['last_login'])

        AuditService.log(
            actor=None,
            tenant=account.tenant,
            action='portal.login',
            entity_type='CustomerAccount',
            entity_id=account.pk,
            ip_address=self._get_ip(request),
        )

        return Response({
            'access': str(access),
            'refresh': str(refresh),
            'lead_id': str(account.lead.pk),
            'lead_status': account.lead.status,
            'user_type': 'customer',
        })

    @staticmethod
    def _get_ip(request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')


# ---------------------------------------------------------------------------
# Token refresh — safe wrapper that returns 401 when user no longer exists
# ---------------------------------------------------------------------------

class TokenRefreshView(_BaseTokenRefreshView):
    """
    POST /api/v1/auth/token/refresh/
    Wraps simplejwt's TokenRefreshView so that a stale refresh token whose
    user has been deleted returns 401 instead of a 500 DoesNotExist crash.
    """

    def post(self, request, *args, **kwargs):
        try:
            return super().post(request, *args, **kwargs)
        except (ObjectDoesNotExist, CustomUser.DoesNotExist):
            raise InvalidToken("Token contained no recognisable user.")


# ---------------------------------------------------------------------------
# Profile & account management views
# ---------------------------------------------------------------------------

class AuthMeView(APIView):
    """GET /api/v1/auth/me/ — return own profile (FM-06)."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class ChangePasswordView(APIView):
    """POST /api/v1/auth/change-password/ — change own password (FM-06)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save(update_fields=['password'])
        AuditService.log_from_request(
            request,
            action='auth.change_password',
            entity_type='CustomUser',
            entity_id=request.user.pk,
        )
        return Response({'detail': 'Password updated.'})


class MFAStatusView(APIView):
    """
    GET  /api/v1/auth/mfa/ — return MFA enrollment status.
    POST /api/v1/auth/mfa/ — scaffold: mark MFA enabled (NFR-SEC-3).
    Full TOTP device management requires a library (e.g. django-otp) in Phase 1.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = MFAStatusSerializer(request.user)
        return Response(serializer.data)

    def post(self, request):
        user = request.user
        user.mfa_enabled = True
        user.save(update_fields=['mfa_enabled'])
        AuditService.log_from_request(
            request,
            action='auth.mfa_enrolled',
            entity_type='CustomUser',
            entity_id=user.pk,
            after_state={'mfa_enabled': True},
        )
        return Response({'detail': 'MFA enabled.'})
