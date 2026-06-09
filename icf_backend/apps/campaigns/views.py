from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status, viewsets
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError
from rest_framework.response import Response

from apps.campaigns.models import Campaign, CampaignEnrollment
from apps.campaigns.selectors import (
    get_campaign_by_id,
    get_campaigns_for_tenant,
    get_enrollment_by_id,
    get_enrollments_for_subject,
)
from apps.campaigns.serializers import (
    CampaignCreateSerializer,
    CampaignEnrollmentSerializer,
    CampaignSerializer,
    EnrollSubjectSerializer,
    StopEnrollmentSerializer,
)
from apps.campaigns.services import CampaignService
from apps.common.mixins import TenantScopedViewMixin
from apps.common.permissions import IsAdvisorOrAbove, IsTeamLeadOrAbove
from apps.leads.models import Lead


def _drf(exc: DjangoValidationError) -> DRFValidationError:
    msgs = list(exc.messages) if hasattr(exc, 'messages') else [str(exc)]
    return DRFValidationError(detail=msgs)


class CampaignViewSet(TenantScopedViewMixin, viewsets.ViewSet):
    """
    FM-09: Campaign CRUD and lifecycle management.
    BRU-01: all queries tenant-scoped.
    """
    permission_classes = [IsAdvisorOrAbove]

    def list(self, request):
        status_filter = request.query_params.get('status')
        qs = get_campaigns_for_tenant(tenant=request.tenant, status=status_filter)
        return Response(CampaignSerializer(qs, many=True).data)

    def retrieve(self, request, pk=None):
        campaign = get_campaign_by_id(tenant=request.tenant, pk=pk)
        if not campaign:
            raise NotFound()
        return Response(CampaignSerializer(campaign).data)

    def create(self, request):
        serializer = CampaignCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            campaign = CampaignService.create_campaign(
                tenant=request.tenant,
                actor=request.user,
                name=serializer.validated_data['name'],
                steps_data=serializer.validated_data.get('steps', []),
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(CampaignSerializer(campaign).data, status=status.HTTP_201_CREATED)


class CampaignActivateView(TenantScopedViewMixin, viewsets.ViewSet):
    """BRU-09: activate — requires at least one step."""
    permission_classes = [IsTeamLeadOrAbove]

    def create(self, request, pk=None):
        campaign = get_campaign_by_id(tenant=request.tenant, pk=pk)
        if not campaign:
            raise NotFound()
        try:
            campaign = CampaignService.activate_campaign(campaign=campaign, actor=request.user)
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(CampaignSerializer(campaign).data)


class CampaignPauseView(TenantScopedViewMixin, viewsets.ViewSet):
    permission_classes = [IsTeamLeadOrAbove]

    def create(self, request, pk=None):
        campaign = get_campaign_by_id(tenant=request.tenant, pk=pk)
        if not campaign:
            raise NotFound()
        try:
            campaign = CampaignService.pause_campaign(campaign=campaign, actor=request.user)
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(CampaignSerializer(campaign).data)


class CampaignEnrollViewSet(TenantScopedViewMixin, viewsets.ViewSet):
    """
    BRU-03/07/21: enroll a lead; stop-on-reply handled via event.
    Every person — Lead, Prospect, Client — is always a Lead record.
    Pass lead_id regardless of their current status in the funnel.
    """
    permission_classes = [IsAdvisorOrAbove]

    def _get_campaign(self, request, campaign_pk):
        campaign = get_campaign_by_id(tenant=request.tenant, pk=campaign_pk)
        if not campaign:
            raise NotFound("Campaign not found.")
        return campaign

    def list(self, request, campaign_pk=None):
        campaign = self._get_campaign(request, campaign_pk)
        qs = campaign.enrollments.all().select_related('lead')
        return Response(CampaignEnrollmentSerializer(qs, many=True).data)

    def create(self, request, campaign_pk=None):
        campaign = self._get_campaign(request, campaign_pk)
        serializer = EnrollSubjectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            lead = Lead.objects.for_tenant(request.tenant).get(
                pk=serializer.validated_data['lead_id']
            )
        except Lead.DoesNotExist:
            raise NotFound("Lead not found.")

        try:
            enrollment = CampaignService.enroll_subject(
                campaign=campaign, actor=request.user, lead=lead,
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(CampaignEnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)


class CampaignEnrollmentStopView(TenantScopedViewMixin, viewsets.ViewSet):
    """BRU-21: manually stop an active enrollment."""
    permission_classes = [IsAdvisorOrAbove]

    def create(self, request, enrollment_pk=None):
        enrollment = get_enrollment_by_id(tenant=request.tenant, pk=enrollment_pk)
        if not enrollment:
            raise NotFound()
        serializer = StopEnrollmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            enrollment = CampaignService.stop_enrollment(
                enrollment=enrollment, actor=request.user,
                reason=serializer.validated_data['reason'],
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(CampaignEnrollmentSerializer(enrollment).data)
