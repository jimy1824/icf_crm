"""
Customer Portal API views.

Architecture rules:
- Views are THIN — they orchestrate only; business logic lives in services/selectors.
- Every view uses CustomerJWTAuthentication + IsCustomerPortalUser.
- Every query is scoped to request.user.lead AND request.user.tenant (BRU-01).
- BRU-08: is_private=True content NEVER returned.
- BRU-14: financial profile is read-only; only phone/preferred_timezone are writable.
- BRU-33: significant actions (document upload, consent change, RSVP) are audited.
- BRU-28: household is consent-gated.
"""

import uuid
from datetime import datetime

from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView


class PortalMessagePagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = 'page_size'
    max_page_size = 100

from apps.audit.services import AuditService
from apps.common.permissions import IsCustomerPortalUser
from apps.communications.models import Communication
from apps.leads.models import ConsentRecord
from apps.portal.authentication import CustomerJWTAuthentication
from apps.portal.selectors import (
    get_portal_advisors,
    get_portal_communications,
    get_portal_consent_records,
    get_portal_document,
    get_portal_documents,
    get_portal_financial_profile,
    get_portal_goal,
    get_portal_goals,
    get_portal_household,
    get_portal_meeting,
    get_portal_meetings,
    get_portal_notifications,
)
from apps.portal.serializers import (
    PortalAdvisorPublicSerializer,
    PortalCommunicationSerializer,
    PortalConsentRecordSerializer,
    PortalConsentUpdateSerializer,
    PortalDashboardSerializer,
    PortalDocumentSerializer,
    PortalDocumentUploadSerializer,
    PortalFinancialSummarySerializer,
    PortalGoalSerializer,
    PortalHouseholdSerializer,
    PortalMeSerializer,
    PortalMeUpdateSerializer,
    PortalMeetingRSVPSerializer,
    PortalMeetingSerializer,
    PortalNotificationSerializer,
    PortalSendMessageSerializer,
)


# Shared auth/permission classes for all portal views
PORTAL_AUTH = [CustomerJWTAuthentication]
PORTAL_PERMS = [IsCustomerPortalUser]


# ---------------------------------------------------------------------------
# GET/PATCH /portal/me/
# ---------------------------------------------------------------------------

class PortalMeView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def get(self, request):
        """Return authenticated customer's account + lead profile."""
        serializer = PortalMeSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        """
        Update client-editable fields only (BRU-14).
        Only phone and preferred_timezone are writable.
        """
        lead = request.user.lead
        serializer = PortalMeUpdateSerializer(lead, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        AuditService.log(
            actor=None,
            tenant=request.user.tenant,
            action='portal.profile.update',
            entity_type='Lead',
            entity_id=lead.pk,
            after_state=serializer.validated_data,
            ip_address=self._get_ip(request),
        )
        return Response(PortalMeSerializer(request.user).data)

    @staticmethod
    def _get_ip(request):
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')


# ---------------------------------------------------------------------------
# GET /portal/financial-summary/
# ---------------------------------------------------------------------------

class PortalFinancialSummaryView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def get(self, request):
        """
        Read-only financial profile summary (BRU-14).
        Returns 404 if no profile exists yet.
        """
        profile = get_portal_financial_profile(lead=request.user.lead)
        if profile is None:
            return Response({'detail': 'No financial profile found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = PortalFinancialSummarySerializer(profile)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# GET /portal/goals/
# GET /portal/goals/<pk>/
# ---------------------------------------------------------------------------

class PortalGoalListView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def get(self, request):
        goals = get_portal_goals(lead=request.user.lead)
        serializer = PortalGoalSerializer(goals, many=True)
        return Response(serializer.data)


class PortalGoalDetailView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def get(self, request, pk):
        goal = get_portal_goal(lead=request.user.lead, goal_pk=pk)
        serializer = PortalGoalSerializer(goal)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# GET /portal/documents/
# POST /portal/documents/
# GET /portal/documents/<pk>/
# ---------------------------------------------------------------------------

class PortalDocumentListView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def get(self, request):
        documents = get_portal_documents(lead=request.user.lead)
        serializer = PortalDocumentSerializer(documents, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        Upload a document (KYC). BRU-33: audited.
        Portal-uploaded documents always start with kyc_status='pending' and version=1.
        storage_ref must be supplied by the frontend (pre-signed upload reference).
        """
        serializer = PortalDocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from apps.documents.models import Document
        doc = Document.objects.create(
            lead=request.user.lead,
            tenant=request.user.tenant,
            doc_type=serializer.validated_data['doc_type'],
            storage_ref=serializer.validated_data['storage_ref'],
            kyc_status=Document.KYC_PENDING,
            version=1,
            uploaded_by=None,  # portal upload — no CustomUser actor
        )
        AuditService.log(
            actor=None,
            tenant=request.user.tenant,
            action='portal.document.upload',
            entity_type='Document',
            entity_id=doc.pk,
            after_state={'doc_type': doc.doc_type, 'kyc_status': doc.kyc_status},
            ip_address=_get_ip(request),
        )
        return Response(PortalDocumentSerializer(doc).data, status=status.HTTP_201_CREATED)


class PortalDocumentDetailView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def get(self, request, pk):
        doc = get_portal_document(lead=request.user.lead, doc_pk=pk)
        serializer = PortalDocumentSerializer(doc)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# GET /portal/meetings/
# PATCH /portal/meetings/<pk>/rsvp/
# ---------------------------------------------------------------------------

class PortalMeetingListView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def get(self, request):
        meetings = get_portal_meetings(lead=request.user.lead)
        serializer = PortalMeetingSerializer(meetings, many=True)
        return Response(serializer.data)


class PortalMeetingRSVPView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def patch(self, request, pk):
        """Accept or decline a meeting. BRU-33: audited."""
        meeting = get_portal_meeting(lead=request.user.lead, meeting_pk=pk)
        serializer = PortalMeetingRSVPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rsvp = serializer.validated_data['rsvp']
        before = {'outcome': meeting.outcome}
        meeting.outcome = rsvp
        meeting.outcome_recorded_at = timezone.now()
        meeting.save(update_fields=['outcome', 'outcome_recorded_at'])

        AuditService.log(
            actor=None,
            tenant=request.user.tenant,
            action='portal.meeting.rsvp',
            entity_type='Meeting',
            entity_id=meeting.pk,
            before_state=before,
            after_state={'outcome': rsvp},
            ip_address=_get_ip(request),
        )
        return Response(PortalMeetingSerializer(meeting).data)


# ---------------------------------------------------------------------------
# GET /portal/messages/
# POST /portal/messages/
# ---------------------------------------------------------------------------

class PortalMessageListView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def get(self, request):
        """
        Return communication timeline for the lead.
        BRU-08: no private content returned (Communications are channel-level events).
        """
        channel = request.query_params.get('channel')
        comms = get_portal_communications(lead=request.user.lead, channel=channel)

        paginator = PortalMessagePagination()
        page = paginator.paginate_queryset(comms, request)
        if page is not None:
            return paginator.get_paginated_response(PortalCommunicationSerializer(page, many=True).data)
        return Response(PortalCommunicationSerializer(comms, many=True).data)

    def post(self, request):
        """
        Send a message to the advisor.
        Creates an inbound Communication record with inline body.
        Channel is always 'email' — customer never picks the channel.
        """
        serializer = PortalSendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        comm = Communication.objects.create(
            lead=request.user.lead,
            tenant=request.user.tenant,
            channel=Communication.CHANNEL_EMAIL,
            direction=Communication.DIRECTION_INBOUND,
            status=Communication.STATUS_RECEIVED,
            subject=serializer.validated_data.get('subject', ''),
            body=serializer.validated_data['body'],
            external_id=str(uuid.uuid4()),  # BRU-16: idempotency key
            sent_at=timezone.now(),
        )
        return Response(
            PortalCommunicationSerializer(comm).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# GET /portal/notifications/
# POST /portal/notifications/<pk>/read/
# POST /portal/notifications/read-all/
# ---------------------------------------------------------------------------

class PortalNotificationListView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def get(self, request):
        notifications = get_portal_notifications(customer_account=request.user)
        serializer = PortalNotificationSerializer(notifications, many=True)
        return Response(serializer.data)


class PortalNotificationReadView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def post(self, request, pk):
        """Mark a single notification as read."""
        from apps.notifications.models import Notification
        from django.shortcuts import get_object_or_404
        notification = get_object_or_404(
            Notification,
            pk=pk,
            tenant=request.user.tenant,
            entity_type='Lead',
            entity_id=str(request.user.lead.pk),
        )
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        return Response({'detail': 'Marked as read.'})


class PortalNotificationReadAllView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def post(self, request):
        """Mark all notifications as read."""
        from apps.notifications.models import Notification
        Notification.objects.filter(
            tenant=request.user.tenant,
            entity_type='Lead',
            entity_id=str(request.user.lead.pk),
            is_read=False,
        ).update(is_read=True)
        return Response({'detail': 'All notifications marked as read.'})


class PortalNotificationUnreadCountView(APIView):
    """Lightweight polling endpoint — returns only the unread count."""
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def get(self, request):
        from apps.notifications.models import Notification
        count = Notification.objects.filter(
            tenant=request.user.tenant,
            entity_type='Lead',
            entity_id=str(request.user.lead.pk),
            is_read=False,
        ).count()
        return Response({'unread_count': count})


# ---------------------------------------------------------------------------
# GET /portal/advisors/
# ---------------------------------------------------------------------------

class PortalAdvisorListView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def get(self, request):
        """Return assigned advisors (public info only — no internal notes)."""
        advisors = get_portal_advisors(lead=request.user.lead)
        serializer = PortalAdvisorPublicSerializer(advisors, many=True)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# GET /portal/consent/
# POST /portal/consent/
# ---------------------------------------------------------------------------

class PortalConsentView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def get(self, request):
        """Return all consent records for this lead (BRU-07/15)."""
        records = get_portal_consent_records(lead=request.user.lead)
        serializer = PortalConsentRecordSerializer(records, many=True)
        return Response(serializer.data)

    def post(self, request):
        """
        Update consent (BRU-07/15). Always creates a NEW record (append-only).
        BRU-33: audited.
        """
        serializer = PortalConsentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        record = ConsentRecord.objects.create(
            lead=request.user.lead,
            tenant=request.user.tenant,
            channel=serializer.validated_data['channel'],
            purpose=serializer.validated_data['purpose'],
            state=serializer.validated_data['state'],
            source=serializer.validated_data.get('source', 'portal'),
        )
        AuditService.log(
            actor=None,
            tenant=request.user.tenant,
            action='portal.consent.update',
            entity_type='ConsentRecord',
            entity_id=record.pk,
            after_state={
                'channel': record.channel,
                'purpose': record.purpose,
                'state': record.state,
            },
            ip_address=_get_ip(request),
        )
        return Response(
            PortalConsentRecordSerializer(record).data,
            status=status.HTTP_201_CREATED,
        )


# ---------------------------------------------------------------------------
# GET /portal/household/
# ---------------------------------------------------------------------------

class PortalHouseholdView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def get(self, request):
        """
        Return household data (BRU-28).
        Only visible if the lead belongs to a household.
        """
        household = get_portal_household(lead=request.user.lead)
        if household is None:
            return Response(
                {'detail': 'No household found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PortalHouseholdSerializer(household)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# GET /portal/dashboard/
# ---------------------------------------------------------------------------

class PortalDashboardView(APIView):
    authentication_classes = PORTAL_AUTH
    permission_classes = PORTAL_PERMS

    def get(self, request):
        """Aggregated dashboard summary for the portal home screen."""
        lead = request.user.lead
        profile = get_portal_financial_profile(lead=lead)
        goals = get_portal_goals(lead=lead)
        notifications = get_portal_notifications(customer_account=request.user)

        now = timezone.now()
        upcoming_meetings = get_portal_meetings(lead=lead).filter(
            scheduled_at__gte=now
        ).count()

        data = {
            'lead_status': lead.status,
            'goals_count': goals.count(),
            'off_track_goals': goals.filter(is_off_track=True).count(),
            'documents_count': get_portal_documents(lead=lead).count(),
            'upcoming_meetings_count': upcoming_meetings,
            'unread_notifications_count': notifications.filter(is_read=False).count(),
            'net_worth': profile.net_worth if profile else None,
        }
        serializer = PortalDashboardSerializer(data)
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    return forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')
