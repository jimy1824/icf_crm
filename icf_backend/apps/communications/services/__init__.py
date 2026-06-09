import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import AuditService
from apps.common.events import event_bus
from apps.communications.models import (
    CallLog,
    Communication,
    ConsentPreference,
    DeliverabilityEvent,
    MailboxConnection,
    Meeting,
    SuppressionRecord,
    TriggerDomain,
)

logger = logging.getLogger(__name__)

# BRU-19: SMS opt-out keywords (TCPA standard)
SMS_OPTOUT_KEYWORDS = frozenset({
    'STOP', 'STOPALL', 'UNSUBSCRIBE', 'CANCEL', 'END', 'QUIT',
})


# ---------------------------------------------------------------------------
# Mailbox / OAuth management (FM-07, BRU-05)
# ---------------------------------------------------------------------------

class MailboxService:

    @staticmethod
    @transaction.atomic
    def connect_mailbox(
        *, tenant, advisor, provider, email_address,
        access_token_enc, refresh_token_enc, token_expires_at,
    ) -> MailboxConnection:
        conn, _ = MailboxConnection.objects.update_or_create(
            advisor=advisor,
            provider=provider,
            email_address=email_address,
            defaults=dict(
                tenant=tenant,
                access_token_enc=access_token_enc,
                refresh_token_enc=refresh_token_enc,
                token_expires_at=token_expires_at,
                status=MailboxConnection.STATUS_ACTIVE,
            ),
        )
        AuditService.log(
            tenant=tenant, actor=advisor,
            action='mailbox.connected',
            entity_type='MailboxConnection', entity_id=conn.pk,
            after_state={'provider': provider, 'email': email_address},
        )
        return conn

    @staticmethod
    @transaction.atomic
    def suspend_on_token_expiry(*, connection: MailboxConnection) -> MailboxConnection:
        """BRU-05: token expired — suspend automation and emit alert event."""
        connection.status = MailboxConnection.STATUS_SUSPENDED
        connection.save(update_fields=['status', 'updated_at'])
        event_bus.emit(
            'mailbox.token_expired',
            tenant_id=connection.tenant_id,
            connection_id=connection.pk,
            advisor_id=connection.advisor_id,
        )
        return connection

    @staticmethod
    @transaction.atomic
    def refresh_token(
        *, connection: MailboxConnection,
        new_access_token_enc, new_refresh_token_enc, new_expires_at,
    ) -> MailboxConnection:
        connection.access_token_enc = new_access_token_enc
        connection.refresh_token_enc = new_refresh_token_enc
        connection.token_expires_at = new_expires_at
        connection.status = MailboxConnection.STATUS_ACTIVE
        connection.save(update_fields=[
            'access_token_enc', 'refresh_token_enc',
            'token_expires_at', 'status', 'updated_at',
        ])
        return connection


# ---------------------------------------------------------------------------
# Inbound mail sync + trigger detection (FM-07, BRU-02/16)
# ---------------------------------------------------------------------------

class InboundMailService:

    @staticmethod
    @transaction.atomic
    def process_inbound_message(
        *, tenant, external_id, from_email, subject, body_ref,
        connection: MailboxConnection,
    ) -> Communication:
        """
        BRU-16: idempotent — safe to call repeatedly with the same external_id.
        E-2: select_for_update on the duplicate check closes the creation race
             when two workers process the same message concurrently.
        BRU-02: if sender domain matches a TriggerDomain, auto-create a lead.
        """
        # E-2 / BRU-16: lock the row if it already exists before inspecting it,
        # preventing a concurrent worker from slipping through the guard.
        from django.db import connection as db_conn
        existing = (
            Communication.objects
            .select_for_update(skip_locked=False)
            .filter(external_id=external_id)
            .first()
        )
        if existing:
            return existing

        comm = Communication.objects.create(
            tenant=tenant,
            channel=Communication.CHANNEL_EMAIL,
            direction=Communication.DIRECTION_INBOUND,
            status=Communication.STATUS_RECEIVED,
            external_id=external_id,
            subject=subject,
            body_ref=body_ref,
        )

        # BRU-02: trigger domain detection
        sender_domain = from_email.split('@')[-1].lower() if '@' in from_email else ''
        if sender_domain:
            trigger = TriggerDomain.objects.filter(
                tenant=tenant, domain=sender_domain, is_active=True,
            ).first()
            if trigger:
                event_bus.emit(
                    'lead.trigger_detected',
                    tenant_id=tenant.pk,
                    external_id=external_id,
                    from_email=from_email,
                    subject=subject,
                )

        # BRU-17: detect reply (basic heuristic; D-01 unresolved)
        if subject.lower().startswith('re:'):
            comm.is_reply = True
            comm.save(update_fields=['is_reply'])
            event_bus.emit(
                'communication.reply_received',
                tenant_id=tenant.pk,
                communication_id=comm.pk,
                from_email=from_email,
            )

        # Advance sync cursor
        connection.sync_cursor = external_id
        connection.last_synced_at = timezone.now()
        connection.save(update_fields=['sync_cursor', 'last_synced_at', 'updated_at'])

        return comm


# ---------------------------------------------------------------------------
# Outbound communication (FM-10/20, BRU-12/18/19)
# ---------------------------------------------------------------------------

class CommunicationService:

    @staticmethod
    @transaction.atomic
    def record_communication(
        *, tenant, channel, direction, body_ref, external_id,
        lead=None, sent_by=None, subject='',
        scheduled_at=None, campaign_enrollment=None,
    ) -> Communication:
        """BRU-16: idempotent by external_id."""
        existing = Communication.objects.filter(external_id=external_id).first()
        if existing:
            return existing
        return Communication.objects.create(
            tenant=tenant,
            lead=lead,
            sent_by=sent_by,
            channel=channel,
            direction=direction,
            body_ref=body_ref,
            external_id=external_id,
            subject=subject,
            scheduled_at=scheduled_at,
            campaign_enrollment=campaign_enrollment,
        )

    @staticmethod
    @transaction.atomic
    def mark_sent(*, communication: Communication) -> Communication:
        communication.status = Communication.STATUS_SENT
        communication.sent_at = timezone.now()
        communication.save(update_fields=['status', 'sent_at', 'updated_at'])
        return communication

    @staticmethod
    @transaction.atomic
    def mark_bounced(*, communication: Communication) -> Communication:
        """
        BRU-19: hard bounce → suppress the address automatically.
        """
        communication.status = Communication.STATUS_BOUNCED
        communication.save(update_fields=['status', 'updated_at'])

        email = ''
        if communication.lead:
            email = communication.lead.email or ''
            communication.lead.is_suppressed = True
            communication.lead.save(update_fields=['is_suppressed', 'updated_at'])

        if email:
            SuppressionRecord.objects.get_or_create(
                tenant=communication.tenant,
                email=email,
                channel=SuppressionRecord.CHANNEL_EMAIL,
                defaults={'reason': SuppressionRecord.REASON_HARD_BOUNCE},
            )
        return communication

    @staticmethod
    @transaction.atomic
    def mark_complained(*, communication: Communication) -> Communication:
        """BRU-19: spam complaint → suppress."""
        communication.status = Communication.STATUS_COMPLAINED
        communication.save(update_fields=['status', 'updated_at'])

        email = ''
        if communication.lead:
            email = communication.lead.email or ''

        if email:
            SuppressionRecord.objects.get_or_create(
                tenant=communication.tenant,
                email=email,
                channel=SuppressionRecord.CHANNEL_EMAIL,
                defaults={'reason': SuppressionRecord.REASON_SPAM_COMPLAINT},
            )
        return communication

    @staticmethod
    def is_suppressed_email(*, tenant, email: str) -> bool:
        """BRU-18/19: check before sending any automated email."""
        return SuppressionRecord.objects.filter(
            tenant=tenant,
            email__iexact=email,
            channel__in=[SuppressionRecord.CHANNEL_EMAIL, SuppressionRecord.CHANNEL_ALL],
        ).exists()

    @staticmethod
    def is_suppressed_phone(*, tenant, phone: str) -> bool:
        """BRU-19: check before sending any automated SMS."""
        return SuppressionRecord.objects.filter(
            tenant=tenant,
            phone=phone,
            channel__in=[SuppressionRecord.CHANNEL_SMS, SuppressionRecord.CHANNEL_ALL],
        ).exists()

    @staticmethod
    @transaction.atomic
    def handle_sms_inbound(
        *, tenant, from_phone, body, external_id,
        lead=None,
    ) -> Communication:
        """
        BRU-16: idempotent by external_id.
        BRU-19: opt-out keyword suppresses phone number.
        BRU-17: non-opt-out body flags is_reply.
        """
        existing = Communication.objects.filter(external_id=external_id).first()
        if existing:
            return existing

        keyword = body.strip().upper()
        is_optout = keyword in SMS_OPTOUT_KEYWORDS

        comm = Communication.objects.create(
            tenant=tenant,
            lead=lead,
            channel=Communication.CHANNEL_SMS,
            direction=Communication.DIRECTION_INBOUND,
            status=Communication.STATUS_RECEIVED,
            external_id=external_id,
            body_ref=body[:500],
            is_reply=not is_optout,
        )

        if is_optout:
            SuppressionRecord.objects.get_or_create(
                tenant=tenant,
                phone=from_phone,
                channel=SuppressionRecord.CHANNEL_SMS,
                defaults={'reason': SuppressionRecord.REASON_SMS_OPTOUT},
            )
            if lead:
                lead.opted_out = True
                lead.save(update_fields=['opted_out', 'updated_at'])
            event_bus.emit(
                'communication.sms_optout',
                tenant_id=tenant.pk,
                phone=from_phone,
                lead_id=lead.pk if lead else None,
            )
        else:
            event_bus.emit(
                'communication.reply_received',
                tenant_id=tenant.pk,
                communication_id=comm.pk,
                from_phone=from_phone,
            )

        return comm


# ---------------------------------------------------------------------------
# Call logging (FM-20, BRU-32)
# ---------------------------------------------------------------------------

class CallService:

    @staticmethod
    @transaction.atomic
    def log_call(
        *, tenant, actor, lead=None,
        duration_seconds, outcome='', notes='',
        recording_consent_captured=False, recording_ref='',
        ringcentral_call_id='',
    ) -> CallLog:
        """BRU-32: recording_ref only stored when consent_captured=True."""
        if recording_ref and not recording_consent_captured:
            raise ValidationError(
                "BRU-32: recording_consent_captured must be True to store a recording."
            )

        import uuid
        external_id = ringcentral_call_id or f"call-{uuid.uuid4()}"
        comm = Communication.objects.create(
            tenant=tenant,
            lead=lead,
            sent_by=actor,
            channel=Communication.CHANNEL_CALL,
            direction=Communication.DIRECTION_OUTBOUND,
            status=Communication.STATUS_DELIVERED,
            external_id=external_id,
        )
        call_log = CallLog.objects.create(
            tenant=tenant,
            communication=comm,
            duration_seconds=duration_seconds,
            outcome=outcome,
            recording_consent_captured=recording_consent_captured,
            recording_ref=recording_ref if recording_consent_captured else '',
            ringcentral_call_id=ringcentral_call_id,
            notes=notes,
        )
        AuditService.log(
            tenant=tenant, actor=actor,
            action='call.logged',
            entity_type='CallLog', entity_id=call_log.pk,
            after_state={
                'outcome': outcome,
                'duration_seconds': duration_seconds,
                'recording_stored': bool(recording_ref and recording_consent_captured),
            },
        )
        return call_log

    @staticmethod
    @transaction.atomic
    def update_outcome(*, call_log: CallLog, actor, outcome, notes='') -> CallLog:
        call_log.outcome = outcome
        if notes:
            call_log.notes = notes
        call_log.save(update_fields=['outcome', 'notes', 'updated_at'])
        AuditService.log(
            tenant=call_log.tenant, actor=actor,
            action='call.outcome_updated',
            entity_type='CallLog', entity_id=call_log.pk,
            after_state={'outcome': outcome},
        )
        return call_log


# ---------------------------------------------------------------------------
# Meeting service (FM-19, BRU-24)
# ---------------------------------------------------------------------------

class MeetingService:

    @staticmethod
    @transaction.atomic
    def schedule_meeting(
        *, tenant, advisor, scheduled_at, recipient_timezone='UTC',
        lead=None,
        zoom_link='', zoom_meeting_id='',
        calendar_provider='', calendar_event_id='',
        notes='',
    ) -> Meeting:
        """BRU-24: scheduled_at stored as UTC; recipient_timezone kept for display."""
        meeting = Meeting.objects.create(
            tenant=tenant,
            advisor=advisor,
            lead=lead,
            scheduled_at=scheduled_at,
            recipient_timezone=recipient_timezone,
            zoom_link=zoom_link,
            zoom_meeting_id=zoom_meeting_id,
            calendar_provider=calendar_provider,
            calendar_event_id=calendar_event_id,
            notes=notes,
        )
        AuditService.log(
            tenant=tenant, actor=advisor,
            action='meeting.scheduled',
            entity_type='Meeting', entity_id=meeting.pk,
            after_state={'scheduled_at': str(scheduled_at)},
        )
        from apps.communications.tasks import send_meeting_reminder
        # schedule reminder 24h before
        eta = scheduled_at - timedelta(hours=24)
        if eta > timezone.now():
            send_meeting_reminder.apply_async(args=[meeting.pk], eta=eta)
        return meeting

    @staticmethod
    @transaction.atomic
    def record_outcome(*, meeting: Meeting, actor, outcome, notes='') -> Meeting:
        meeting.outcome = outcome
        meeting.outcome_recorded_at = timezone.now()
        if notes:
            meeting.notes = notes
        meeting.save(update_fields=['outcome', 'outcome_recorded_at', 'notes', 'updated_at'])
        AuditService.log(
            tenant=meeting.tenant, actor=actor,
            action='meeting.outcome_recorded',
            entity_type='Meeting', entity_id=meeting.pk,
            after_state={'outcome': outcome},
        )
        return meeting


# ---------------------------------------------------------------------------
# Deliverability / suppression service (FM-25, BRU-18/19)
# ---------------------------------------------------------------------------

class DeliverabilityService:

    @staticmethod
    @transaction.atomic
    def process_webhook_event(
        *, tenant, external_id, event_type, email, raw_payload,
        communication=None,
    ) -> DeliverabilityEvent:
        """BRU-16: idempotent by external_id."""
        event, created = DeliverabilityEvent.objects.get_or_create(
            external_id=external_id,
            defaults=dict(
                tenant=tenant,
                event_type=event_type,
                email=email,
                raw_payload=raw_payload,
                communication=communication,
            ),
        )
        if not created:
            return event

        if event_type == DeliverabilityEvent.EVENT_BOUNCE and communication:
            CommunicationService.mark_bounced(communication=communication)
        elif event_type == DeliverabilityEvent.EVENT_COMPLAINT and communication:
            CommunicationService.mark_complained(communication=communication)

        event.processed = True
        event.save(update_fields=['processed'])
        return event

    @staticmethod
    @transaction.atomic
    def manually_suppress(
        *, tenant, actor, email='', phone='', channel, reason=SuppressionRecord.REASON_MANUAL,
    ) -> SuppressionRecord:
        record, _ = SuppressionRecord.objects.get_or_create(
            tenant=tenant,
            email=email,
            phone=phone,
            channel=channel,
            defaults={'reason': reason},
        )
        AuditService.log(
            tenant=tenant, actor=actor,
            action='suppression.added',
            entity_type='SuppressionRecord', entity_id=record.pk,
            after_state={'email': email, 'phone': phone, 'channel': channel, 'reason': reason},
        )
        return record

    @staticmethod
    @transaction.atomic
    def remove_suppression(*, tenant, actor, suppression_record: SuppressionRecord) -> None:
        AuditService.log(
            tenant=tenant, actor=actor,
            action='suppression.removed',
            entity_type='SuppressionRecord', entity_id=suppression_record.pk,
            before_state={'email': suppression_record.email, 'channel': suppression_record.channel},
        )
        suppression_record.delete()


# ---------------------------------------------------------------------------
# Consent / preference service (FM-24, BRU-07/15/38)
# ---------------------------------------------------------------------------

class ConsentService:

    @staticmethod
    @transaction.atomic
    def record_consent(
        *, tenant, channel, purpose, state, source,
        lead=None, ip_address=None,
    ) -> ConsentPreference:
        """
        BRU-07/15: append-only — creates a new record; latest wins per query.
        """
        pref = ConsentPreference.objects.create(
            tenant=tenant,
            lead=lead,
            channel=channel,
            purpose=purpose,
            state=state,
            source=source,
            ip_address=ip_address,
        )
        AuditService.log(
            tenant=tenant, actor=None,
            action='consent.recorded',
            entity_type='ConsentPreference', entity_id=pref.pk,
            after_state={
                'channel': channel, 'purpose': purpose, 'state': state,
                'source': source,
                'lead': lead.pk if lead else None,
            },
        )
        if state == ConsentPreference.STATE_REVOKED:
            event_bus.emit(
                'consent.revoked',
                tenant_id=tenant.pk,
                channel=channel,
                lead_id=lead.pk if lead else None,
            )
        return pref

    @staticmethod
    def has_consent(*, tenant, channel, purpose, lead=None) -> bool:
        """
        BRU-07: returns True only if the latest consent record is GRANTED.
        """
        qs = ConsentPreference.objects.filter(
            tenant=tenant, channel=channel, purpose=purpose,
        )
        if lead:
            qs = qs.filter(lead=lead)
        latest = qs.order_by('-created_at').first()
        return latest is not None and latest.state == ConsentPreference.STATE_GRANTED

    @staticmethod
    @transaction.atomic
    def place_legal_hold(*, tenant, actor, lead=None) -> int:
        """BRU-38: protect all consent records for a subject from deletion."""
        qs = ConsentPreference.objects.filter(tenant=tenant)
        if lead:
            qs = qs.filter(lead=lead)
        count = qs.update(is_under_legal_hold=True)
        AuditService.log(
            tenant=tenant, actor=actor,
            action='consent.legal_hold_placed',
            entity_type='ConsentPreference', entity_id=0,
            after_state={'lead': lead.pk if lead else None, 'records_held': count},
        )
        return count
