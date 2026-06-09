from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.mixins import TenantScopedViewMixin
from apps.common.permissions import IsAdvisorOrAbove, IsTenantAdminOrAbove
from apps.timezones.serializers import (
    AdvisorTimeZoneSerializer,
    AdvisorTimeZoneWriteSerializer,
    TenantTimeZoneSerializer,
    TenantTimeZoneUpdateSerializer,
)
from apps.timezones.services import TimezoneService


def _drf(exc: DjangoValidationError) -> DRFValidationError:
    msgs = list(exc.messages) if hasattr(exc, 'messages') else [str(exc)]
    return DRFValidationError(detail=msgs)


class TenantTimeZoneView(TenantScopedViewMixin, APIView):
    """
    GET  /timezones/tenant/   — retrieve tenant timezone config
    PATCH /timezones/tenant/  — update tenant timezone config (Tenant Admin+)
    """

    def get_permissions(self):
        if self.request.method == 'GET':
            return [IsAdvisorOrAbove()]
        return [IsTenantAdminOrAbove()]

    def get(self, request):
        config = TimezoneService.get_tenant_config(request.tenant)
        return Response(TenantTimeZoneSerializer(config).data)

    def patch(self, request):
        serializer = TenantTimeZoneUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            config = TimezoneService.update_tenant_config(
                tenant=request.tenant,
                actor=request.user,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(TenantTimeZoneSerializer(config).data)


class AdvisorTimeZoneView(TenantScopedViewMixin, APIView):
    """
    GET  /timezones/advisor/   — retrieve requesting advisor's timezone config
    PUT  /timezones/advisor/   — set advisor's personal timezone override
    """
    permission_classes = [IsAdvisorOrAbove]

    def get(self, request):
        try:
            config = request.user.timezone_config
            return Response(AdvisorTimeZoneSerializer(config).data)
        except Exception:
            return Response({'timezone': None})

    def put(self, request):
        serializer = AdvisorTimeZoneWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            config = TimezoneService.set_advisor_timezone(
                advisor=request.user,
                timezone_str=serializer.validated_data['timezone'],
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(AdvisorTimeZoneSerializer(config).data, status=status.HTTP_200_OK)
