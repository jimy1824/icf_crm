from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.campaign_timeline.selectors import (
    get_advisor_timeline,
    get_timeline_for_campaign,
    get_timeline_for_enrollment,
    get_timeline_for_lead,
)
from apps.campaign_timeline.serializers import (
    TimelineDashboardSerializer,
    TimelineEntrySerializer,
)
from apps.campaign_timeline.services import TimelineAnalyticsService
from apps.common.mixins import TenantScopedViewMixin
from apps.common.permissions import IsAdvisorOrAbove, IsTenantAdminOrAbove


class LeadTimelineView(TenantScopedViewMixin, APIView):
    """
    GET /timeline/leads/<lead_id>/
    Returns the full execution timeline for a lead across all campaigns.
    BRU-01: tenant-scoped.
    """
    permission_classes = [IsAdvisorOrAbove]

    def get(self, request, lead_id=None):
        from apps.leads.models import Lead
        try:
            lead = Lead.objects.for_tenant(request.tenant).get(pk=lead_id)
        except Lead.DoesNotExist:
            raise NotFound("Lead not found.")
        qs = get_timeline_for_lead(tenant=request.tenant, lead=lead)
        return Response(TimelineEntrySerializer(qs, many=True).data)


class CampaignTimelineView(TenantScopedViewMixin, APIView):
    """
    GET /timeline/campaigns/<campaign_id>/
    Returns timeline entries across all enrolled leads for a campaign.
    BRU-01: tenant-scoped.
    """
    permission_classes = [IsAdvisorOrAbove]

    def get(self, request, campaign_id=None):
        from apps.campaigns.models import Campaign
        try:
            campaign = Campaign.objects.for_tenant(request.tenant).get(pk=campaign_id)
        except Campaign.DoesNotExist:
            raise NotFound("Campaign not found.")
        qs = get_timeline_for_campaign(tenant=request.tenant, campaign=campaign)
        return Response(TimelineEntrySerializer(qs, many=True).data)


class EnrollmentTimelineView(TenantScopedViewMixin, APIView):
    """
    GET /timeline/enrollments/<enrollment_id>/
    Returns timeline entries for a specific enrollment.
    BRU-01: tenant-scoped.
    """
    permission_classes = [IsAdvisorOrAbove]

    def get(self, request, enrollment_id=None):
        from apps.campaigns.models import CampaignEnrollment
        try:
            enrollment = CampaignEnrollment.objects.for_tenant(request.tenant).get(
                pk=enrollment_id,
            )
        except CampaignEnrollment.DoesNotExist:
            raise NotFound("Enrollment not found.")
        qs = get_timeline_for_enrollment(tenant=request.tenant, enrollment=enrollment)
        return Response(TimelineEntrySerializer(qs, many=True).data)


class AdvisorTimelineView(TenantScopedViewMixin, APIView):
    """
    GET /timeline/advisor/
    Returns upcoming pending timeline entries for the requesting advisor's leads.
    Accepts ?hours_ahead=N (default 48).
    """
    permission_classes = [IsAdvisorOrAbove]

    def get(self, request):
        try:
            hours = int(request.query_params.get('hours_ahead', 48))
        except (ValueError, TypeError):
            hours = 48
        qs = get_advisor_timeline(
            tenant=request.tenant,
            advisor=request.user,
            hours_ahead=hours,
        )
        return Response(TimelineEntrySerializer(qs, many=True).data)


class TimelineDashboardView(TenantScopedViewMixin, APIView):
    """
    GET /timeline/dashboard/
    Returns aggregated counts for the admin dashboard.
    BRU-01: tenant-scoped. Tenant Admin+ only.
    """
    permission_classes = [IsTenantAdminOrAbove]

    def get(self, request):
        data = TimelineAnalyticsService.dashboard_summary(tenant=request.tenant)
        serializer = TimelineDashboardSerializer(data=data)
        serializer.is_valid()
        return Response(serializer.data)
