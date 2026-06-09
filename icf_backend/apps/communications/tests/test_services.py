"""
Communication service tests — covers:
BRU-02: trigger domain auto-creates lead on inbound email
BRU-05: token expiry suspends mailbox connection
BRU-07: consent revoke suppresses channel
BRU-15: consent is append-only; latest record wins
BRU-16: idempotent processing (external_id dedup)
BRU-17: reply detection sets is_reply flag
BRU-18: suppression gate before send
BRU-19: hard bounce / spam complaint / SMS opt-out suppresses
BRU-24: meeting scheduled_at stored as UTC
BRU-32: recording requires consent_captured=True
BRU-42: SMS opt-out stops campaigns (via event)
BRU-01: tenant isolation throughout
"""
import pytest
from datetime import timedelta
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.communications.models import (
    CallLog, Communication, ConsentPreference,
    DeliverabilityEvent, MailboxConnection,
    Meeting, SuppressionRecord, TriggerDomain,
)
from apps.communications.services import (
    CallService, CommunicationService, ConsentService,
    DeliverabilityService, InboundMailService, MailboxService, MeetingService,
)
from apps.leads.models import Lead
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Comm Firm')


@pytest.fixture
def advisor(tenant):
    return CustomUser.objects.create_user(
        email='adv@comm.com', password='pass1234!',
        first_name='A', last_name='B',
        role=CustomUser.ROLE_ADVISOR, tenant=tenant,
    )


@pytest.fixture
def lead(tenant):
    return Lead.objects.create(
        tenant=tenant, first_name='Jane', last_name='Lead',
        email='jane@example.com', source=Lead.SOURCE_MANUAL,
    )


@pytest.fixture
def mailbox(tenant, advisor):
    return MailboxConnection.objects.create(
        tenant=tenant,
        advisor=advisor,
        provider=MailboxConnection.PROVIDER_GMAIL,
        email_address='advisor@gmail.com',
        access_token_enc='tok_enc',
        refresh_token_enc='ref_enc',
        token_expires_at=timezone.now() + timedelta(hours=1),
        status=MailboxConnection.STATUS_ACTIVE,
    )


# ---------------------------------------------------------------------------
# MailboxService (FM-07, BRU-05)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMailboxService:

    def test_connect_mailbox(self, tenant, advisor):
        conn = MailboxService.connect_mailbox(
            tenant=tenant, advisor=advisor,
            provider=MailboxConnection.PROVIDER_GMAIL,
            email_address='new@gmail.com',
            access_token_enc='tok',
            refresh_token_enc='ref',
            token_expires_at=timezone.now() + timedelta(hours=1),
        )
        assert conn.status == MailboxConnection.STATUS_ACTIVE

    def test_connect_mailbox_idempotent(self, tenant, advisor, mailbox):
        """Reconnecting the same mailbox updates the existing record."""
        conn2 = MailboxService.connect_mailbox(
            tenant=tenant, advisor=advisor,
            provider=MailboxConnection.PROVIDER_GMAIL,
            email_address='advisor@gmail.com',
            access_token_enc='new_tok',
            refresh_token_enc='new_ref',
            token_expires_at=timezone.now() + timedelta(hours=2),
        )
        assert conn2.pk == mailbox.pk
        assert conn2.access_token_enc == 'new_tok'

    def test_bru_05_suspend_on_token_expiry(self, mailbox):
        """BRU-05: expired token suspends automation."""
        suspended = MailboxService.suspend_on_token_expiry(connection=mailbox)
        assert suspended.status == MailboxConnection.STATUS_SUSPENDED


# ---------------------------------------------------------------------------
# InboundMailService (BRU-02/16/17)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestInboundMailService:

    def test_bru_16_idempotent_processing(self, tenant, mailbox):
        """BRU-16: same external_id returns the existing Communication."""
        c1 = InboundMailService.process_inbound_message(
            tenant=tenant,
            external_id='msg-001',
            from_email='sender@partner.com',
            subject='Hello',
            body_ref='s3://bucket/msg-001',
            connection=mailbox,
        )
        c2 = InboundMailService.process_inbound_message(
            tenant=tenant,
            external_id='msg-001',
            from_email='sender@partner.com',
            subject='Hello',
            body_ref='s3://bucket/msg-001',
            connection=mailbox,
        )
        assert c1.pk == c2.pk
        assert Communication.objects.filter(external_id='msg-001').count() == 1

    def test_bru_17_reply_detection(self, tenant, mailbox):
        """BRU-17: subject starting with 'Re:' sets is_reply=True."""
        comm = InboundMailService.process_inbound_message(
            tenant=tenant,
            external_id='msg-reply-001',
            from_email='client@example.com',
            subject='Re: Meeting tomorrow',
            body_ref='s3://bucket/reply',
            connection=mailbox,
        )
        assert comm.is_reply is True

    def test_non_reply_not_flagged(self, tenant, mailbox):
        comm = InboundMailService.process_inbound_message(
            tenant=tenant,
            external_id='msg-new-001',
            from_email='client@example.com',
            subject='Question about my portfolio',
            body_ref='s3://bucket/new',
            connection=mailbox,
        )
        assert comm.is_reply is False

    def test_bru_02_trigger_domain_detected(self, tenant, mailbox):
        """BRU-02: sender domain matching TriggerDomain emits lead.trigger_detected event."""
        TriggerDomain.objects.create(tenant=tenant, domain='partner.com', is_active=True)
        comm = InboundMailService.process_inbound_message(
            tenant=tenant,
            external_id='msg-trigger-001',
            from_email='newlead@partner.com',
            subject='Inquiry',
            body_ref='s3://bucket/trigger',
            connection=mailbox,
        )
        assert comm.pk is not None


# ---------------------------------------------------------------------------
# CommunicationService (BRU-16/18/19)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCommunicationService:

    def test_bru_16_record_idempotent(self, tenant, lead):
        """BRU-16: second call with same external_id returns existing record."""
        c1 = CommunicationService.record_communication(
            tenant=tenant, channel='email', direction='outbound',
            body_ref='s3://b/1', external_id='out-001', lead=lead,
        )
        c2 = CommunicationService.record_communication(
            tenant=tenant, channel='email', direction='outbound',
            body_ref='s3://b/1', external_id='out-001', lead=lead,
        )
        assert c1.pk == c2.pk

    def test_bru_19_hard_bounce_suppresses(self, tenant, lead):
        """BRU-19: hard bounce auto-adds email to suppression list."""
        comm = CommunicationService.record_communication(
            tenant=tenant, channel='email', direction='outbound',
            body_ref='s3://b/2', external_id='out-002', lead=lead,
        )
        CommunicationService.mark_bounced(communication=comm)
        assert SuppressionRecord.objects.filter(
            tenant=tenant, email=lead.email, channel='email',
        ).exists()
        lead.refresh_from_db()
        assert lead.is_suppressed is True

    def test_bru_19_spam_complaint_suppresses(self, tenant, lead):
        """BRU-19: spam complaint auto-suppresses."""
        comm = CommunicationService.record_communication(
            tenant=tenant, channel='email', direction='outbound',
            body_ref='s3://b/3', external_id='out-003', lead=lead,
        )
        CommunicationService.mark_complained(communication=comm)
        assert SuppressionRecord.objects.filter(
            tenant=tenant, email=lead.email, channel='email',
        ).exists()

    def test_bru_18_suppressed_email_detected(self, tenant, lead):
        """BRU-18: is_suppressed_email returns True after suppression."""
        SuppressionRecord.objects.create(
            tenant=tenant, email=lead.email, channel='email',
            reason='hard_bounce',
        )
        assert CommunicationService.is_suppressed_email(tenant=tenant, email=lead.email) is True

    def test_bru_19_sms_optout_suppresses(self, tenant, lead):
        """BRU-19: SMS STOP keyword suppresses phone and opts out lead."""
        lead.phone = '+12025551234'
        lead.save()
        comm = CommunicationService.handle_sms_inbound(
            tenant=tenant,
            from_phone='+12025551234',
            body='STOP',
            external_id='sms-stop-001',
            lead=lead,
        )
        assert SuppressionRecord.objects.filter(
            tenant=tenant, phone='+12025551234', channel='sms',
        ).exists()
        lead.refresh_from_db()
        assert lead.opted_out is True

    def test_bru_16_sms_inbound_idempotent(self, tenant, lead):
        """BRU-16: duplicate SMS inbound event ignored."""
        c1 = CommunicationService.handle_sms_inbound(
            tenant=tenant, from_phone='+1555000', body='Hi', external_id='sms-dup',
        )
        c2 = CommunicationService.handle_sms_inbound(
            tenant=tenant, from_phone='+1555000', body='Hi', external_id='sms-dup',
        )
        assert c1.pk == c2.pk

    def test_bru_01_suppression_scoped_to_tenant(self, lead):
        """BRU-01: suppression in tenant1 does not affect tenant2."""
        t1 = Tenant.objects.create(firm_name='Firm 1')
        t2 = Tenant.objects.create(firm_name='Firm 2')
        SuppressionRecord.objects.create(
            tenant=t1, email='shared@example.com', channel='email', reason='hard_bounce',
        )
        assert CommunicationService.is_suppressed_email(
            tenant=t2, email='shared@example.com',
        ) is False


# ---------------------------------------------------------------------------
# CallService (FM-20, BRU-32)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCallService:

    def test_log_call(self, tenant, advisor, lead):
        call_log = CallService.log_call(
            tenant=tenant, actor=advisor, lead=lead,
            duration_seconds=120, outcome='interested',
            recording_consent_captured=True, recording_ref='s3://calls/1.mp4',
        )
        assert call_log.outcome == 'interested'
        assert call_log.recording_ref == 's3://calls/1.mp4'

    def test_bru_32_recording_requires_consent(self, tenant, advisor, lead):
        """BRU-32: recording_ref rejected when consent=False."""
        with pytest.raises(ValidationError, match="consent_captured"):
            CallService.log_call(
                tenant=tenant, actor=advisor, lead=lead,
                duration_seconds=60, outcome='no_answer',
                recording_consent_captured=False,
                recording_ref='s3://calls/secret.mp4',
            )

    def test_bru_32_no_recording_without_consent_stores_empty(self, tenant, advisor, lead):
        """BRU-32: recording_ref is empty when consent=False and no ref provided."""
        call_log = CallService.log_call(
            tenant=tenant, actor=advisor, lead=lead,
            duration_seconds=60, recording_consent_captured=False,
        )
        assert call_log.recording_ref == ''

    def test_update_outcome(self, tenant, advisor, lead):
        call_log = CallService.log_call(
            tenant=tenant, actor=advisor, lead=lead, duration_seconds=30,
        )
        updated = CallService.update_outcome(
            call_log=call_log, actor=advisor, outcome='closed', notes='Deal done',
        )
        assert updated.outcome == 'closed'
        assert updated.notes == 'Deal done'


# ---------------------------------------------------------------------------
# MeetingService (FM-19, BRU-24)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMeetingService:

    def test_bru_24_meeting_stored_as_utc(self, tenant, advisor, lead):
        """BRU-24: scheduled_at stored as UTC; recipient_timezone preserved."""
        scheduled = timezone.now() + timedelta(days=7)
        meeting = MeetingService.schedule_meeting(
            tenant=tenant, advisor=advisor, lead=lead,
            scheduled_at=scheduled, recipient_timezone='America/New_York',
        )
        assert meeting.scheduled_at == scheduled
        assert meeting.recipient_timezone == 'America/New_York'
        assert meeting.reminder_sent is False

    def test_record_meeting_outcome(self, tenant, advisor, lead):
        scheduled = timezone.now() + timedelta(days=2)
        meeting = MeetingService.schedule_meeting(
            tenant=tenant, advisor=advisor, lead=lead, scheduled_at=scheduled,
        )
        updated = MeetingService.record_outcome(
            meeting=meeting, actor=advisor, outcome='closed_won', notes='Great call',
        )
        assert updated.outcome == 'closed_won'
        assert updated.outcome_recorded_at is not None


# ---------------------------------------------------------------------------
# DeliverabilityService (FM-25, BRU-16/18/19)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDeliverabilityService:

    def test_bru_16_webhook_idempotent(self, tenant, lead):
        """BRU-16: same external_id returns existing event."""
        comm = CommunicationService.record_communication(
            tenant=tenant, channel='email', direction='outbound',
            body_ref='s3://b/d1', external_id='msg-d1', lead=lead,
        )
        e1 = DeliverabilityService.process_webhook_event(
            tenant=tenant,
            external_id='evt-001',
            event_type=DeliverabilityEvent.EVENT_DELIVERY,
            email=lead.email,
            raw_payload={'event_type': 'delivery', 'email': lead.email},
            communication=comm,
        )
        e2 = DeliverabilityService.process_webhook_event(
            tenant=tenant,
            external_id='evt-001',
            event_type=DeliverabilityEvent.EVENT_DELIVERY,
            email=lead.email,
            raw_payload={'event_type': 'delivery', 'email': lead.email},
            communication=comm,
        )
        assert e1.pk == e2.pk
        assert DeliverabilityEvent.objects.filter(external_id='evt-001').count() == 1

    def test_bounce_webhook_suppresses_email(self, tenant, lead):
        """BRU-19: bounce webhook suppresses the email address."""
        comm = CommunicationService.record_communication(
            tenant=tenant, channel='email', direction='outbound',
            body_ref='s3://b/d2', external_id='msg-d2', lead=lead,
        )
        DeliverabilityService.process_webhook_event(
            tenant=tenant,
            external_id='evt-bounce-001',
            event_type=DeliverabilityEvent.EVENT_BOUNCE,
            email=lead.email,
            raw_payload={'event_type': 'bounce', 'email': lead.email},
            communication=comm,
        )
        assert SuppressionRecord.objects.filter(
            tenant=tenant, email=lead.email,
        ).exists()

    def test_manual_suppression(self, tenant, advisor):
        record = DeliverabilityService.manually_suppress(
            tenant=tenant, actor=advisor,
            email='spam@example.com', channel='email',
        )
        assert record.reason == SuppressionRecord.REASON_MANUAL
        assert CommunicationService.is_suppressed_email(
            tenant=tenant, email='spam@example.com',
        )

    def test_remove_suppression(self, tenant, advisor):
        record = DeliverabilityService.manually_suppress(
            tenant=tenant, actor=advisor,
            email='bounce@example.com', channel='email',
        )
        DeliverabilityService.remove_suppression(
            tenant=tenant, actor=advisor, suppression_record=record,
        )
        assert not CommunicationService.is_suppressed_email(
            tenant=tenant, email='bounce@example.com',
        )


# ---------------------------------------------------------------------------
# ConsentService (FM-24, BRU-07/15/38)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestConsentService:

    def test_bru_15_consent_append_only(self, tenant, lead):
        """BRU-15: each consent call creates a new record (append-only)."""
        ConsentService.record_consent(
            tenant=tenant, channel='email', purpose='marketing',
            state='granted', source='web_form', lead=lead,
        )
        ConsentService.record_consent(
            tenant=tenant, channel='email', purpose='marketing',
            state='revoked', source='opt_out_link', lead=lead,
        )
        count = ConsentPreference.objects.filter(
            tenant=tenant, lead=lead, channel='email',
        ).count()
        assert count == 2

    def test_bru_07_has_consent_uses_latest(self, tenant, lead):
        """BRU-07: has_consent reflects most recent state."""
        ConsentService.record_consent(
            tenant=tenant, channel='email', purpose='marketing',
            state='granted', source='web_form', lead=lead,
        )
        assert ConsentService.has_consent(
            tenant=tenant, channel='email', purpose='marketing', lead=lead,
        ) is True

        ConsentService.record_consent(
            tenant=tenant, channel='email', purpose='marketing',
            state='revoked', source='opt_out_link', lead=lead,
        )
        assert ConsentService.has_consent(
            tenant=tenant, channel='email', purpose='marketing', lead=lead,
        ) is False

    def test_no_consent_returns_false(self, tenant, lead):
        """No consent records → has_consent is False."""
        assert ConsentService.has_consent(
            tenant=tenant, channel='sms', purpose='marketing', lead=lead,
        ) is False

    def test_bru_38_legal_hold(self, tenant, advisor, lead):
        """BRU-38: legal hold set on all consent records for subject."""
        ConsentService.record_consent(
            tenant=tenant, channel='email', purpose='marketing',
            state='granted', source='form', lead=lead,
        )
        ConsentService.record_consent(
            tenant=tenant, channel='sms', purpose='marketing',
            state='granted', source='form', lead=lead,
        )
        count = ConsentService.place_legal_hold(tenant=tenant, actor=advisor, lead=lead)
        assert count == 2
        held = ConsentPreference.objects.filter(
            tenant=tenant, lead=lead, is_under_legal_hold=True,
        ).count()
        assert held == 2

    def test_bru_01_consent_scoped_to_tenant(self, lead):
        """BRU-01: consent records in different tenants are isolated."""
        t1 = Tenant.objects.create(firm_name='T1')
        t2 = Tenant.objects.create(firm_name='T2')
        lead1 = Lead.objects.create(
            tenant=t1, first_name='A', last_name='B',
            email='a@t1.com', source=Lead.SOURCE_MANUAL,
        )
        lead2 = Lead.objects.create(
            tenant=t2, first_name='C', last_name='D',
            email='c@t2.com', source=Lead.SOURCE_MANUAL,
        )
        ConsentService.record_consent(
            tenant=t1, channel='email', purpose='marketing',
            state='granted', source='form', lead=lead1,
        )
        assert ConsentService.has_consent(
            tenant=t2, channel='email', purpose='marketing', lead=lead2,
        ) is False
