from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from django.core.exceptions import ValidationError as DjValidationError
from rest_framework.exceptions import ValidationError as DRFValidationError, NotFound

from apps.common.permissions import IsAdvisorOrAbove, IsTenantAdmin
from apps.territories.models import Territory, AdvisorTerritory
from apps.territories.serializers import (
    TerritorySerializer,
    TerritoryCreateSerializer,
    TerritoryUpdateSerializer,
    AdvisorTerritorySerializer,
    AssignAdvisorSerializer,
)
from apps.territories.services import TerritoryService, TerritoryAnalyticsService
from apps.territories.selectors import (
    get_territories_for_tenant,
    get_territory_by_id,
    get_advisors_for_territory,
    get_territories_for_advisor,
)


def _drf(exc: DjValidationError):
    return DRFValidationError(detail=exc.messages if hasattr(exc, 'messages') else str(exc))


def _get_territory(pk, tenant):
    try:
        return get_territory_by_id(territory_id=pk, tenant=tenant)
    except Territory.DoesNotExist:
        raise NotFound("Territory not found.")


# ---------------------------------------------------------------------------
# Territory CRUD
# ---------------------------------------------------------------------------

class TerritoryListCreateView(APIView):
    """
    GET  /territories/        — list all active territories for the tenant
    POST /territories/        — create territory (TenantAdmin only)
    """

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsTenantAdmin()]
        return [IsAuthenticated(), IsAdvisorOrAbove()]

    def get(self, request):
        qs = get_territories_for_tenant(tenant=request.user.tenant, active_only=False)
        return Response(TerritorySerializer(qs, many=True).data)

    def post(self, request):
        serializer = TerritoryCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            territory = TerritoryService.create_territory(
                tenant=request.user.tenant,
                actor=request.user,
                **serializer.validated_data,
            )
        except DjValidationError as exc:
            raise _drf(exc)
        return Response(TerritorySerializer(territory).data, status=status.HTTP_201_CREATED)


class TerritoryDetailView(APIView):
    """
    GET   /territories/<pk>/  — retrieve
    PATCH /territories/<pk>/  — update (TenantAdmin)
    DELETE /territories/<pk>/ — soft-delete (TenantAdmin)
    """

    def get_permissions(self):
        if self.request.method in ('PATCH', 'DELETE'):
            return [IsAuthenticated(), IsTenantAdmin()]
        return [IsAuthenticated(), IsAdvisorOrAbove()]

    def get(self, request, pk):
        territory = _get_territory(pk, request.user.tenant)
        return Response(TerritorySerializer(territory).data)

    def patch(self, request, pk):
        territory = _get_territory(pk, request.user.tenant)
        serializer = TerritoryUpdateSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        try:
            territory = TerritoryService.update_territory(
                territory=territory,
                actor=request.user,
                **serializer.validated_data,
            )
        except DjValidationError as exc:
            raise _drf(exc)
        return Response(TerritorySerializer(territory).data)

    def delete(self, request, pk):
        territory = _get_territory(pk, request.user.tenant)
        TerritoryService.deactivate_territory(territory=territory, actor=request.user)
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Advisor ↔ Territory assignment
# ---------------------------------------------------------------------------

class TerritoryAdvisorsView(APIView):
    """
    GET    /territories/<pk>/advisors/            — list advisors in territory
    POST   /territories/<pk>/assign-advisor/      — assign advisor (TenantAdmin)
    """

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsTenantAdmin()]
        return [IsAuthenticated(), IsAdvisorOrAbove()]

    def get(self, request, pk):
        territory = _get_territory(pk, request.user.tenant)
        assignments = get_advisors_for_territory(territory=territory)
        return Response(AdvisorTerritorySerializer(assignments, many=True).data)

    def post(self, request, pk):
        territory = _get_territory(pk, request.user.tenant)
        serializer = AssignAdvisorSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from apps.users.models import CustomUser
        try:
            advisor = CustomUser.objects.get(
                pk=serializer.validated_data['advisor_id'],
                tenant=request.user.tenant,
            )
        except CustomUser.DoesNotExist:
            raise NotFound("Advisor not found in this tenant.")
        try:
            assignment = TerritoryService.assign_advisor(
                territory=territory, advisor=advisor, actor=request.user,
            )
        except DjValidationError as exc:
            raise _drf(exc)
        return Response(AdvisorTerritorySerializer(assignment).data, status=status.HTTP_201_CREATED)


class TerritoryAdvisorRemoveView(APIView):
    """DELETE /territories/<pk>/advisors/<advisor_pk>/  — remove advisor from territory"""

    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def delete(self, request, pk, advisor_pk):
        territory = _get_territory(pk, request.user.tenant)
        from apps.users.models import CustomUser
        try:
            advisor = CustomUser.objects.get(
                pk=advisor_pk, tenant=request.user.tenant,
            )
        except CustomUser.DoesNotExist:
            raise NotFound("Advisor not found in this tenant.")
        TerritoryService.remove_advisor(
            territory=territory, advisor=advisor, actor=request.user,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdvisorTerritoriesView(APIView):
    """GET /territories/advisor/<advisor_pk>/  — list territories for a specific advisor"""

    permission_classes = [IsAuthenticated, IsAdvisorOrAbove]

    def get(self, request, advisor_pk):
        from apps.users.models import CustomUser
        try:
            advisor = CustomUser.objects.get(pk=advisor_pk, tenant=request.user.tenant)
        except CustomUser.DoesNotExist:
            raise NotFound("Advisor not found in this tenant.")
        territories = get_territories_for_advisor(advisor=advisor, tenant=request.user.tenant)
        return Response(TerritorySerializer(territories, many=True).data)


# ---------------------------------------------------------------------------
# Analytics views
# ---------------------------------------------------------------------------

class TerritorySummaryView(APIView):
    """GET /territories/<pk>/analytics/summary/"""

    permission_classes = [IsAuthenticated, IsAdvisorOrAbove]

    def get(self, request, pk):
        territory = _get_territory(pk, request.user.tenant)
        data = TerritoryAnalyticsService.territory_summary(
            tenant=request.user.tenant, territory=territory,
        )
        return Response(data)


class TerritoryWeeklyView(APIView):
    """GET /territories/<pk>/analytics/weekly/"""

    permission_classes = [IsAuthenticated, IsAdvisorOrAbove]

    def get(self, request, pk):
        territory = _get_territory(pk, request.user.tenant)
        data = TerritoryAnalyticsService.territory_weekly(
            tenant=request.user.tenant, territory=territory,
        )
        return Response(data)


class AdvisorTerritoryAnalyticsView(APIView):
    """GET /territories/analytics/advisor/<advisor_pk>/"""

    permission_classes = [IsAuthenticated, IsAdvisorOrAbove]

    def get(self, request, advisor_pk):
        from apps.users.models import CustomUser
        try:
            advisor = CustomUser.objects.get(pk=advisor_pk, tenant=request.user.tenant)
        except CustomUser.DoesNotExist:
            raise NotFound("Advisor not found.")
        data = TerritoryAnalyticsService.advisor_territory_analytics(
            tenant=request.user.tenant, advisor=advisor,
        )
        return Response(data)


class TerritoryGraphLeadsView(APIView):
    """GET /territories/analytics/graph/leads/"""

    permission_classes = [IsAuthenticated, IsAdvisorOrAbove]

    def get(self, request):
        data = TerritoryAnalyticsService.graph_leads_per_territory(tenant=request.user.tenant)
        return Response(data)


class TerritoryGraphAdvisorsView(APIView):
    """GET /territories/analytics/graph/advisors/"""

    permission_classes = [IsAuthenticated, IsAdvisorOrAbove]

    def get(self, request):
        data = TerritoryAnalyticsService.graph_advisors_per_territory(tenant=request.user.tenant)
        return Response(data)


class TerritoryGraphWeeklyTrendView(APIView):
    """GET /territories/analytics/graph/weekly-trend/?weeks=8"""

    permission_classes = [IsAuthenticated, IsAdvisorOrAbove]

    def get(self, request):
        try:
            weeks = int(request.query_params.get('weeks', 8))
            weeks = max(1, min(weeks, 52))
        except (ValueError, TypeError):
            weeks = 8
        data = TerritoryAnalyticsService.graph_weekly_trend(
            tenant=request.user.tenant, weeks=weeks,
        )
        return Response(data)


class TerritoryGraphCampaignsView(APIView):
    """GET /territories/analytics/graph/campaigns/"""

    permission_classes = [IsAuthenticated, IsAdvisorOrAbove]

    def get(self, request):
        data = TerritoryAnalyticsService.graph_campaign_performance(tenant=request.user.tenant)
        return Response(data)


class TerritoryGraphConversionView(APIView):
    """GET /territories/analytics/graph/conversion/"""

    permission_classes = [IsAuthenticated, IsAdvisorOrAbove]

    def get(self, request):
        data = TerritoryAnalyticsService.graph_conversion_rate(tenant=request.user.tenant)
        return Response(data)
