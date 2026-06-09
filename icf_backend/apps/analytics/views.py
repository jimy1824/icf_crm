"""
FM-12 Analytics API views.
All tenant-facing views are BRU-01 scoped — tenant is resolved from request.user.
Dashboard section views (2 & 3) support full server-side pagination, sorting,
filtering, and search — never client-side.
"""
from datetime import date as date_type

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.models import AnalyticsSnapshot
from apps.analytics.selectors import (
    get_tenant_advisors,
    get_today_leads_queryset,
    get_today_activities_queryset,
)
from apps.analytics.serializers import (
    AnalyticsSnapshotSerializer,
    AdvisorSummarySerializer,
    TodayLeadRowSerializer,
    TodayActivityRowSerializer,
)
from apps.analytics.services import AnalyticsService
from apps.common.permissions import IsSuperAdmin


# ─── Pagination ────────────────────────────────────────────────────────────────

class DashboardPagePagination(PageNumberPagination):
    """
    20 rows per page by default; caller may pass ?page_size= up to 100.
    Response envelope: { count, next, previous, results }
    """
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ─── Existing dashboard endpoints ─────────────────────────────────────────────

class FirmDashboardView(APIView):
    """FM-12: live firm-level dashboard KPIs. Tenant Admin / Team Lead."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = AnalyticsService.firm_dashboard(tenant=request.user.tenant)
        return Response(data)


class AdvisorDashboardView(APIView):
    """FM-12: advisor's own KPIs."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = AnalyticsService.advisor_dashboard(
            tenant=request.user.tenant, advisor=request.user,
        )
        return Response(data)


class ClientDashboardView(APIView):
    """FM-12: client-level KPIs. Requires lead_id query param (Lead IS the client entity)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.leads.models import Lead
        lead_id = request.query_params.get('lead_id') or request.query_params.get('client_id')
        if not lead_id:
            return Response({'detail': 'lead_id required.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            lead = Lead.objects.get(pk=lead_id, tenant=request.user.tenant)
        except Lead.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        data = AnalyticsService.client_dashboard(tenant=request.user.tenant, lead=lead)
        return Response(data)


class PlatformDashboardView(APIView):
    """FM-12: platform-wide KPIs. Super Admin only."""
    permission_classes = [IsAuthenticated, IsSuperAdmin]

    def get(self, request):
        data = AnalyticsService.platform_dashboard()
        return Response(data)


class AnalyticsSnapshotListView(APIView):
    """FM-26: list historical snapshots for the tenant."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        level = request.query_params.get('level', AnalyticsSnapshot.LEVEL_FIRM)
        qs = AnalyticsSnapshot.objects.filter(
            tenant=request.user.tenant, level=level,
        ).order_by('-snapshot_date')[:90]
        serializer = AnalyticsSnapshotSerializer(qs, many=True)
        return Response(serializer.data)


# ─── New: Advisors list ────────────────────────────────────────────────────────

class TenantAdvisorsView(APIView):
    """
    GET /api/v1/analytics/advisors/
    Returns active advisors (role=advisor|team_lead) for the current tenant.
    Used as a filter source in the dashboard tables.
    BRU-01: tenant-scoped — only this tenant's advisors are returned.
    Managers and Admins are excluded (role filter is strict).
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = get_tenant_advisors(tenant=request.user.tenant)
        serializer = AdvisorSummarySerializer(qs, many=True)
        return Response({'results': serializer.data, 'count': qs.count()})


# ─── New dashboard section endpoints ─────────────────────────────────────────

class WeeklyLeadAnalyticsView(APIView):
    """
    FM-12 Dashboard Section 1: weekly lead analytics.
    GET /api/v1/analytics/weekly-leads/?days=7&scope=my|company
    days: 7 (default), 15, or 30.
    scope: 'my' filters to the calling advisor; 'company' returns firm-wide.
    BRU-01: always tenant-scoped.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            days = int(request.query_params.get('days', 7))
        except (TypeError, ValueError):
            days = 7
        days = days if days in (7, 15, 30) else 7

        scope = request.query_params.get('scope', 'my')
        advisor = request.user if scope == 'my' else None

        data = AnalyticsService.weekly_lead_analytics(
            tenant=request.user.tenant, days=days, advisor=advisor,
        )
        return Response({'days': days, 'scope': scope, 'data': data})


class TodayLeadsView(APIView):
    """
    FM-12 Dashboard Section 2: today's leads — enterprise data table.

    GET /api/v1/analytics/today-leads/
      ?advisor_id=<id>|all    — omit → logged-in advisor (my scope)
      &date=YYYY-MM-DD        — omit → today
      &page=1
      &page_size=20
      &ordering=created_at|-created_at|last_name|pipeline_stage|territory__name
      &search=<term>          — searches first_name, last_name, email, phone

    Response: standard DRF paginated envelope { count, next, previous, results }

    BRU-01: queryset is always filtered by tenant first.
    No client-side sorting or pagination — all server-side.
    """
    permission_classes = [IsAuthenticated]
    _ALLOWED_ORDERING = {
        'created_at', '-created_at',
        'last_name', '-last_name',
        'first_name', '-first_name',
        'pipeline_stage', '-pipeline_stage',
        'status', '-status',
        'territory__name', '-territory__name',
    }

    def get(self, request):
        tenant = request.user.tenant

        # ── advisor filter ────────────────────────────────────────────
        from apps.users.models import CustomUser
        advisor_id = request.query_params.get('advisor_id')
        advisor = None
        if advisor_id and advisor_id != 'all':
            try:
                advisor = CustomUser.objects.get(
                    pk=advisor_id, tenant=tenant,
                    role__in=[CustomUser.ROLE_ADVISOR, CustomUser.ROLE_TEAM_LEAD],
                )
            except CustomUser.DoesNotExist:
                return Response(
                    {'detail': 'Advisor not found or not in this tenant.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
        elif advisor_id is None:
            # Default: scope to the logged-in user when they are an advisor/team_lead
            if request.user.role in CustomUser.ADVISOR_ROLES:
                advisor = request.user

        # ── date filter ───────────────────────────────────────────────
        date_param = request.query_params.get('date')
        on_date = None
        if date_param:
            try:
                on_date = date_type.fromisoformat(date_param)
            except ValueError:
                return Response(
                    {'detail': 'Invalid date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # ── search ────────────────────────────────────────────────────
        search = request.query_params.get('search', '').strip() or None

        # ── base queryset ─────────────────────────────────────────────
        qs = get_today_leads_queryset(
            tenant=tenant, advisor=advisor, on_date=on_date, search=search,
        )

        # ── ordering ──────────────────────────────────────────────────
        ordering = request.query_params.get('ordering', '-created_at')
        if ordering not in self._ALLOWED_ORDERING:
            ordering = '-created_at'
        qs = qs.order_by(ordering)

        # ── paginate ──────────────────────────────────────────────────
        paginator = DashboardPagePagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = TodayLeadRowSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class TodayActivitiesView(APIView):
    """
    FM-12 Dashboard Section 3: today's scheduled activities — enterprise data table.

    GET /api/v1/analytics/today-activities/
      ?advisor_id=<id>|all
      &date=YYYY-MM-DD
      &page=1
      &page_size=20
      &ordering=scheduled_at|-scheduled_at|step_order|status|campaign__name
      &search=<term>          — searches lead name, campaign name

    Response: standard DRF paginated envelope { count, next, previous, results }

    BRU-01: queryset is always filtered by tenant first.
    """
    permission_classes = [IsAuthenticated]
    _ALLOWED_ORDERING = {
        'scheduled_at', '-scheduled_at',
        'step_order', '-step_order',
        'status', '-status',
        'campaign__name', '-campaign__name',
        'lead__last_name', '-lead__last_name',
    }

    def get(self, request):
        tenant = request.user.tenant

        # ── advisor filter ────────────────────────────────────────────
        advisor_id = request.query_params.get('advisor_id')
        advisor = None
        if advisor_id and advisor_id != 'all':
            from apps.users.models import CustomUser
            try:
                advisor = CustomUser.objects.get(
                    pk=advisor_id, tenant=tenant,
                    role__in=[CustomUser.ROLE_ADVISOR, CustomUser.ROLE_TEAM_LEAD],
                )
            except CustomUser.DoesNotExist:
                return Response(
                    {'detail': 'Advisor not found or not in this tenant.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
        elif advisor_id is None:
            from apps.users.models import CustomUser
            if request.user.role in CustomUser.ADVISOR_ROLES:
                advisor = request.user

        # ── date filter ───────────────────────────────────────────────
        date_param = request.query_params.get('date')
        on_date = None
        if date_param:
            try:
                on_date = date_type.fromisoformat(date_param)
            except ValueError:
                return Response(
                    {'detail': 'Invalid date format. Use YYYY-MM-DD.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # ── search ────────────────────────────────────────────────────
        search = request.query_params.get('search', '').strip() or None

        # ── base queryset ─────────────────────────────────────────────
        qs = get_today_activities_queryset(
            tenant=tenant, advisor=advisor, on_date=on_date, search=search,
        )

        # ── ordering ──────────────────────────────────────────────────
        ordering = request.query_params.get('ordering', 'scheduled_at')
        if ordering not in self._ALLOWED_ORDERING:
            ordering = 'scheduled_at'
        qs = qs.order_by(ordering)

        # ── paginate ──────────────────────────────────────────────────
        paginator = DashboardPagePagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = TodayActivityRowSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class TodayResponsesView(APIView):
    """
    FM-12 Dashboard Section 4: inbound lead replies received today.
    GET /api/v1/analytics/today-responses/?scope=my|company
    BRU-01: tenant-scoped.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        scope = request.query_params.get('scope', 'my')
        advisor = request.user if scope == 'my' else None
        data = AnalyticsService.today_responses(
            tenant=request.user.tenant, advisor=advisor,
        )
        return Response({'scope': scope, 'results': data, 'count': len(data)})


class TerritoryLeadDistributionView(APIView):
    """
    FM-12 Dashboard Section 5: territory lead distribution (horizontal bar chart).
    GET /api/v1/analytics/territory-distribution/?days=7
    BRU-01: tenant-scoped.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            days = int(request.query_params.get('days', 7))
        except (TypeError, ValueError):
            days = 7
        days = days if days in (7, 15, 30) else 7

        data = AnalyticsService.territory_lead_distribution(
            tenant=request.user.tenant, days=days,
        )
        return Response({'days': days, 'results': data})
