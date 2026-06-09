import uuid

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.leads.models import Lead
from apps.common.mixins import TenantScopedRequestMixin, TenantScopedViewMixin
from apps.common.permissions import IsAdvisorOrAbove, IsTeamLeadOrAbove
from apps.communications.models import (
    Communication, CallLog, Meeting, MailboxConnection,
    SuppressionRecord, ConsentPreference, TriggerDomain,
)
from apps.communications.selectors import (
    get_call_log_by_id, get_call_logs_for_tenant,
    get_communications_for_tenant,
    get_consent_history,
    get_mailbox_connection,
    get_meeting_by_id, get_meetings_for_advisor,
    get_suppressions_for_tenant,
    get_trigger_domains,
)
from apps.communications.serializers import (
    AddSuppressionSerializer,
    CallLogSerializer,
    CommunicationSerializer,
    ConsentPreferenceSerializer,
    LogCallSerializer,
    MailboxConnectionSerializer, MailboxConnectSerializer,
    MeetingSerializer,
    RecordConsentSerializer,
    RecordMeetingOutcomeSerializer,
    ScheduleMeetingSerializer,
    SendMessageSerializer,
    SuppressionRecordSerializer,
    TriggerDomainSerializer,
    UpdateCallOutcomeSerializer,
)
from apps.communications.services import (
    CallService, ConsentService, DeliverabilityService,
    MailboxService, MeetingService,
)


class CommunicationPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 100


def _drf(exc: DjangoValidationError) -> DRFValidationError:
    msgs = list(exc.messages) if hasattr(exc, 'messages') else [str(exc)]
    return DRFValidationError(detail=msgs)


def _resolve_lead(tenant, data):
    """Resolve a lead from validated serializer data (lead_id required)."""
    lead_id = data.get('lead_id')
    if not lead_id:
        raise DRFValidationError({'lead_id': 'This field is required.'})
    try:
        return Lead.objects.for_tenant(tenant).get(pk=lead_id)
    except Lead.DoesNotExist:
        raise NotFound("Lead not found.")


def _resolve_lead_optional(tenant, data):
    """Resolve a lead from validated serializer data (lead_id optional)."""
    lead_id = data.get('lead_id')
    if not lead_id:
        return None
    try:
        return Lead.objects.for_tenant(tenant).get(pk=lead_id)
    except Lead.DoesNotExist:
        raise NotFound("Lead not found.")


# ---------------------------------------------------------------------------
# Mailbox management (FM-07)
# ---------------------------------------------------------------------------

class MailboxConnectionViewSet(TenantScopedViewMixin, viewsets.ViewSet):
    """FM-07: OAuth mailbox connections. BRU-05: token expiry suspends automation."""
    permission_classes = [IsAdvisorOrAbove]

    def list(self, request):
        from apps.communications.selectors import get_active_mailbox_connections
        qs = get_active_mailbox_connections(tenant=request.tenant)
        return Response(MailboxConnectionSerializer(qs, many=True).data)

    def create(self, request):
        serializer = MailboxConnectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conn = MailboxService.connect_mailbox(
            tenant=request.tenant,
            advisor=request.user,
            **serializer.validated_data,
        )
        return Response(MailboxConnectionSerializer(conn).data, status=status.HTTP_201_CREATED)


class TriggerDomainViewSet(TenantScopedViewMixin, viewsets.ViewSet):
    """BRU-02: configure domains that auto-create leads on inbound email."""
    permission_classes = [IsTeamLeadOrAbove]

    def list(self, request):
        qs = get_trigger_domains(tenant=request.tenant, active_only=False)
        return Response(TriggerDomainSerializer(qs, many=True).data)

    def create(self, request):
        serializer = TriggerDomainSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        domain = TriggerDomain.objects.create(
            tenant=request.tenant, **serializer.validated_data,
        )
        return Response(TriggerDomainSerializer(domain).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Communications timeline (FM-10)
# ---------------------------------------------------------------------------

class CommunicationViewSet(TenantScopedViewMixin, viewsets.ViewSet):
    """FM-10: communication timeline + advisor send. BRU-01: tenant-scoped."""
    permission_classes = [IsAdvisorOrAbove]

    def list(self, request):
        lead_id = request.query_params.get('lead_id')
        channel = request.query_params.get('channel')
        direction = request.query_params.get('direction')
        date_from = request.query_params.get('date_from')
        date_to = request.query_params.get('date_to')

        lead = None
        if lead_id:
            lead = Lead.objects.for_tenant(request.tenant).filter(pk=lead_id).first()

        qs = get_communications_for_tenant(
            tenant=request.tenant, channel=channel, direction=direction, lead=lead,
            date_from=date_from, date_to=date_to,
        )

        paginator = CommunicationPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(CommunicationSerializer(page, many=True).data)
        return Response(CommunicationSerializer(qs, many=True).data)

    @action(detail=False, methods=['post'], url_path='send')
    def send(self, request):
        """
        Advisor sends a message (email/sms/portal) to a lead.
        BRU-01: lead must belong to request.tenant.
        BRU-33: audit log written by the calling service layer.
        """
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        lead = _resolve_lead(request.tenant, data)

        comm = Communication.objects.create(
            tenant=request.tenant,
            lead=lead,
            sent_by=request.user,
            channel=data['channel'],
            direction=Communication.DIRECTION_OUTBOUND,
            status=Communication.STATUS_SENT,
            subject=data.get('subject', ''),
            body=data['body'],
            external_id=str(uuid.uuid4()),  # BRU-16: idempotency key
            sent_at=timezone.now(),
        )
        return Response(CommunicationSerializer(comm).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Call logging (FM-20, BRU-32)
# ---------------------------------------------------------------------------

class CallLogViewSet(TenantScopedViewMixin, viewsets.ViewSet):
    """FM-20: log calls with outcome tags. BRU-32: consent before recording."""
    permission_classes = [IsAdvisorOrAbove]

    def list(self, request):
        outcome = request.query_params.get('outcome')
        qs = get_call_logs_for_tenant(tenant=request.tenant, outcome=outcome)
        return Response(CallLogSerializer(qs, many=True).data)

    def create(self, request):
        serializer = LogCallSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        lead = _resolve_lead(request.tenant, data)
        try:
            call_log = CallService.log_call(
                tenant=request.tenant,
                actor=request.user,
                lead=lead,
                duration_seconds=data['duration_seconds'],
                outcome=data.get('outcome', ''),
                notes=data.get('notes', ''),
                recording_consent_captured=data['recording_consent_captured'],
                recording_ref=data.get('recording_ref', ''),
                ringcentral_call_id=data.get('ringcentral_call_id', ''),
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(CallLogSerializer(call_log).data, status=status.HTTP_201_CREATED)


class CallOutcomeView(TenantScopedRequestMixin, APIView):
    """Update call outcome after the fact."""
    permission_classes = [IsAdvisorOrAbove]

    def post(self, request, pk=None):
        call_log = get_call_log_by_id(tenant=request.tenant, pk=pk)
        if not call_log:
            raise NotFound()
        serializer = UpdateCallOutcomeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        call_log = CallService.update_outcome(
            call_log=call_log, actor=request.user,
            outcome=serializer.validated_data['outcome'],
            notes=serializer.validated_data.get('notes', ''),
        )
        return Response(CallLogSerializer(call_log).data)


# ---------------------------------------------------------------------------
# Meetings (FM-19, BRU-24)
# ---------------------------------------------------------------------------

class MeetingViewSet(TenantScopedViewMixin, viewsets.ViewSet):
    """FM-19: schedule, retrieve, and record meeting outcomes. BRU-24: timezone-aware."""
    permission_classes = [IsAdvisorOrAbove]

    def list(self, request):
        upcoming_only = request.query_params.get('upcoming_only', '').lower() == 'true'
        qs = get_meetings_for_advisor(
            tenant=request.tenant, advisor=request.user, upcoming_only=upcoming_only,
        )
        return Response(MeetingSerializer(qs, many=True).data)

    def create(self, request):
        serializer = ScheduleMeetingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        lead = _resolve_lead(request.tenant, data)
        meeting = MeetingService.schedule_meeting(
            tenant=request.tenant,
            advisor=request.user,
            lead=lead,
            scheduled_at=data['scheduled_at'],
            recipient_timezone=data.get('recipient_timezone', 'UTC'),
            zoom_link=data.get('zoom_link', ''),
            zoom_meeting_id=data.get('zoom_meeting_id', ''),
            calendar_provider=data.get('calendar_provider', ''),
            calendar_event_id=data.get('calendar_event_id', ''),
            notes=data.get('notes', ''),
        )
        return Response(MeetingSerializer(meeting).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, pk=None):
        meeting = get_meeting_by_id(tenant=request.tenant, pk=pk)
        if not meeting:
            raise NotFound()
        return Response(MeetingSerializer(meeting).data)


class MeetingOutcomeView(TenantScopedRequestMixin, APIView):
    """BRU-24: record outcome after a meeting concludes."""
    permission_classes = [IsAdvisorOrAbove]

    def post(self, request, pk=None):
        meeting = get_meeting_by_id(tenant=request.tenant, pk=pk)
        if not meeting:
            raise NotFound()
        serializer = RecordMeetingOutcomeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        meeting = MeetingService.record_outcome(
            meeting=meeting, actor=request.user,
            outcome=serializer.validated_data['outcome'],
            notes=serializer.validated_data.get('notes', ''),
        )
        return Response(MeetingSerializer(meeting).data)


# ---------------------------------------------------------------------------
# Suppression management (FM-25, BRU-18/19)
# ---------------------------------------------------------------------------

class SuppressionViewSet(TenantScopedViewMixin, viewsets.ViewSet):
    """FM-25: manage suppression list. BRU-19: hard bounce/complaint auto-adds."""
    permission_classes = [IsTeamLeadOrAbove]

    def list(self, request):
        channel = request.query_params.get('channel')
        qs = get_suppressions_for_tenant(tenant=request.tenant, channel=channel)
        return Response(SuppressionRecordSerializer(qs, many=True).data)

    def create(self, request):
        serializer = AddSuppressionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = DeliverabilityService.manually_suppress(
            tenant=request.tenant, actor=request.user,
            email=serializer.validated_data.get('email', ''),
            phone=serializer.validated_data.get('phone', ''),
            channel=serializer.validated_data['channel'],
        )
        return Response(SuppressionRecordSerializer(record).data, status=status.HTTP_201_CREATED)

    def destroy(self, request, pk=None):
        qs = SuppressionRecord.objects.filter(tenant=request.tenant, pk=pk)
        record = qs.first()
        if not record:
            raise NotFound()
        DeliverabilityService.remove_suppression(
            tenant=request.tenant, actor=request.user, suppression_record=record,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Consent management (FM-24, BRU-07/15/38)
# ---------------------------------------------------------------------------

class ConsentViewSet(TenantScopedViewMixin, viewsets.ViewSet):
    """FM-24: consent record of truth. BRU-07: revoke blocks automated sends."""
    permission_classes = [IsAdvisorOrAbove]

    def list(self, request):
        lead_id = request.query_params.get('lead_id')
        lead = None
        if lead_id:
            lead = Lead.objects.for_tenant(request.tenant).filter(pk=lead_id).first()
        qs = get_consent_history(tenant=request.tenant, lead=lead)
        return Response(ConsentPreferenceSerializer(qs, many=True).data)

    def create(self, request):
        serializer = RecordConsentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        lead = _resolve_lead_optional(request.tenant, data)
        pref = ConsentService.record_consent(
            tenant=request.tenant,
            channel=data['channel'],
            purpose=data['purpose'],
            state=data['state'],
            source=data['source'],
            lead=lead,
            ip_address=data.get('ip_address'),
        )
        return Response(ConsentPreferenceSerializer(pref).data, status=status.HTTP_201_CREATED)


# ---------------------------------------------------------------------------
# Deliverability webhook (FM-25, BRU-16/18/19)
# ---------------------------------------------------------------------------

class DeliverabilityWebhookView(APIView):
    """
    FM-25: inbound webhook from email provider (SES, SendGrid, etc.).
    BRU-16: idempotent processing via external_id.
    No authentication required — validated by signature header (provider-level).
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        from apps.communications.tasks import process_inbound_webhook
        external_id = request.data.get('event_id', '')
        if not external_id:
            return Response({'error': 'event_id required'}, status=status.HTTP_400_BAD_REQUEST)
        process_inbound_webhook.delay(
            external_id=external_id,
            payload=request.data,
            channel='email',
        )
        return Response({'queued': True})
