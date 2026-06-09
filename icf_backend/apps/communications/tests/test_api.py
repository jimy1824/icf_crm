"""
Communications API tests.
BRU-01: tenant isolation.
BRU-24: meeting timezone.
BRU-32: call recording consent.
BRU-18/19: suppression management.
BRU-07/15: consent record.
BRU-16: deliverability webhook idempotency.
"""
import pytest
from datetime import timedelta
from django.utils import timezone
from rest_framework.test import APIClient

from apps.communications.models import (
    Communication, ConsentPreference, MailboxConnection,
    Meeting, SuppressionRecord,
)
from apps.leads.models import Lead
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Comm API Firm')


@pytest.fixture
def advisor(tenant):
    return CustomUser.objects.create_user(
        email='adv_comm@firm.com', password='pass1234!',
        first_name='A', last_name='B',
        role=CustomUser.ROLE_ADVISOR, tenant=tenant,
    )


@pytest.fixture
def team_lead(tenant):
    return CustomUser.objects.create_user(
        email='tl_comm@firm.com', password='pass1234!',
        first_name='T', last_name='L',
        role=CustomUser.ROLE_TEAM_LEAD, tenant=tenant,
    )


@pytest.fixture
def lead(tenant):
    return Lead.objects.create(
        tenant=tenant, first_name='Test', last_name='Lead',
        email='test@lead.com', source=Lead.SOURCE_MANUAL,
    )


@pytest.fixture
def auth_client(advisor):
    c = APIClient()
    c.force_authenticate(user=advisor)
    return c


@pytest.fixture
def tl_client(team_lead):
    c = APIClient()
    c.force_authenticate(user=team_lead)
    return c


# ---------------------------------------------------------------------------
# Mailbox (FM-07)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMailboxAPI:

    def test_connect_mailbox(self, auth_client):
        resp = auth_client.post('/api/v1/communications/mailboxes/', {
            'provider': 'gmail',
            'email_address': 'advisor@gmail.com',
            'access_token_enc': 'tok',
            'refresh_token_enc': 'ref',
            'token_expires_at': (timezone.now() + timedelta(hours=1)).isoformat(),
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['status'] == 'active'

    def test_list_mailboxes(self, auth_client, advisor, tenant):
        MailboxConnection.objects.create(
            tenant=tenant, advisor=advisor,
            provider='gmail', email_address='a@g.com',
            access_token_enc='t', refresh_token_enc='r',
            token_expires_at=timezone.now() + timedelta(hours=1),
        )
        resp = auth_client.get('/api/v1/communications/mailboxes/')
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_unauthenticated_blocked(self):
        c = APIClient()
        resp = c.get('/api/v1/communications/mailboxes/')
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Call logging (FM-20, BRU-32)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCallAPI:

    def test_log_call(self, auth_client, lead):
        resp = auth_client.post('/api/v1/communications/calls/', {
            'lead_id': lead.pk,
            'duration_seconds': 120,
            'outcome': 'interested',
            'recording_consent_captured': True,
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['outcome'] == 'interested'

    def test_bru_32_recording_without_consent_rejected(self, auth_client, lead):
        """BRU-32: recording_ref blocked when consent=False."""
        resp = auth_client.post('/api/v1/communications/calls/', {
            'lead_id': lead.pk,
            'duration_seconds': 60,
            'recording_consent_captured': False,
            'recording_ref': 's3://calls/secret.mp4',
        }, format='json')
        assert resp.status_code == 400

    def test_update_call_outcome(self, auth_client, lead):
        # Create call first
        create_resp = auth_client.post('/api/v1/communications/calls/', {
            'lead_id': lead.pk,
            'duration_seconds': 90,
        }, format='json')
        assert create_resp.status_code == 201
        call_id = create_resp.data['id']
        resp = auth_client.post(f'/api/v1/communications/calls/{call_id}/outcome/', {
            'outcome': 'follow_up',
            'notes': 'Call back next week',
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['outcome'] == 'follow_up'

    def test_missing_lead_and_client_rejected(self, auth_client):
        resp = auth_client.post('/api/v1/communications/calls/', {
            'duration_seconds': 30,
        }, format='json')
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# Meetings (FM-19, BRU-24)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestMeetingAPI:

    def test_schedule_meeting(self, auth_client, lead):
        scheduled = (timezone.now() + timedelta(days=7)).isoformat()
        resp = auth_client.post('/api/v1/communications/meetings/', {
            'lead_id': lead.pk,
            'scheduled_at': scheduled,
            'recipient_timezone': 'America/Chicago',
            'zoom_link': 'https://zoom.us/j/12345',
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['recipient_timezone'] == 'America/Chicago'

    def test_bru_24_timezone_preserved(self, auth_client, lead):
        scheduled = (timezone.now() + timedelta(days=3)).isoformat()
        resp = auth_client.post('/api/v1/communications/meetings/', {
            'lead_id': lead.pk,
            'scheduled_at': scheduled,
            'recipient_timezone': 'America/Los_Angeles',
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['recipient_timezone'] == 'America/Los_Angeles'

    def test_record_meeting_outcome(self, auth_client, lead):
        scheduled = (timezone.now() + timedelta(days=1)).isoformat()
        create_resp = auth_client.post('/api/v1/communications/meetings/', {
            'lead_id': lead.pk,
            'scheduled_at': scheduled,
        }, format='json')
        meeting_id = create_resp.data['id']
        resp = auth_client.post(f'/api/v1/communications/meetings/{meeting_id}/outcome/', {
            'outcome': 'closed_won',
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['outcome'] == 'closed_won'

    def test_bru_01_meeting_not_visible_cross_tenant(self):
        t1 = Tenant.objects.create(firm_name='T1')
        t2 = Tenant.objects.create(firm_name='T2')
        adv1 = CustomUser.objects.create_user(
            email='a@t1.com', password='pass!',
            first_name='A', last_name='A',
            role=CustomUser.ROLE_ADVISOR, tenant=t1,
        )
        adv2 = CustomUser.objects.create_user(
            email='b@t2.com', password='pass!',
            first_name='B', last_name='B',
            role=CustomUser.ROLE_ADVISOR, tenant=t2,
        )
        lead1 = Lead.objects.create(
            tenant=t1, first_name='X', last_name='Y',
            email='x@t1.com', source=Lead.SOURCE_MANUAL,
        )
        Meeting.objects.create(
            tenant=t1, advisor=adv1, lead=lead1,
            scheduled_at=timezone.now() + timedelta(days=1),
        )
        c2 = APIClient()
        c2.force_authenticate(user=adv2)
        resp = c2.get('/api/v1/communications/meetings/')
        assert resp.status_code == 200
        assert len(resp.data) == 0


# ---------------------------------------------------------------------------
# Suppression (FM-25, BRU-18/19)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSuppressionAPI:

    def test_add_suppression(self, tl_client):
        resp = tl_client.post('/api/v1/communications/suppression/', {
            'email': 'bounce@example.com',
            'channel': 'email',
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['email'] == 'bounce@example.com'

    def test_list_suppression(self, tl_client, tenant):
        SuppressionRecord.objects.create(
            tenant=tenant, email='x@y.com', channel='email', reason='hard_bounce',
        )
        resp = tl_client.get('/api/v1/communications/suppression/')
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_delete_suppression(self, tl_client, tenant):
        r = SuppressionRecord.objects.create(
            tenant=tenant, email='rem@x.com', channel='email', reason='manual',
        )
        resp = tl_client.delete(f'/api/v1/communications/suppression/{r.pk}/')
        assert resp.status_code == 204
        assert not SuppressionRecord.objects.filter(pk=r.pk).exists()

    def test_advisor_cannot_manage_suppression(self, auth_client):
        """Only team lead or above can manage suppression."""
        resp = auth_client.post('/api/v1/communications/suppression/', {
            'email': 'x@y.com',
            'channel': 'email',
        }, format='json')
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Consent (FM-24, BRU-07/15)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestConsentAPI:

    def test_record_consent(self, auth_client, lead):
        resp = auth_client.post('/api/v1/communications/consent/', {
            'lead_id': lead.pk,
            'channel': 'email',
            'purpose': 'marketing',
            'state': 'granted',
            'source': 'web_form',
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['state'] == 'granted'

    def test_bru_15_consent_is_append_only(self, auth_client, lead):
        """BRU-15: each POST creates a new record — not an update."""
        auth_client.post('/api/v1/communications/consent/', {
            'lead_id': lead.pk, 'channel': 'email', 'purpose': 'marketing',
            'state': 'granted', 'source': 'form',
        }, format='json')
        auth_client.post('/api/v1/communications/consent/', {
            'lead_id': lead.pk, 'channel': 'email', 'purpose': 'marketing',
            'state': 'revoked', 'source': 'opt_out',
        }, format='json')
        count = ConsentPreference.objects.filter(lead=lead, channel='email').count()
        assert count == 2

    def test_list_consent_history(self, auth_client, lead, tenant):
        ConsentPreference.objects.create(
            tenant=tenant, lead=lead, channel='email',
            purpose='marketing', state='granted', source='form',
        )
        resp = auth_client.get(f'/api/v1/communications/consent/?lead_id={lead.pk}')
        assert resp.status_code == 200
        assert len(resp.data) == 1


# ---------------------------------------------------------------------------
# Deliverability webhook (BRU-16)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDeliverabilityWebhook:

    def test_webhook_accepted(self):
        c = APIClient()
        resp = c.post('/api/v1/communications/webhooks/deliverability/', {
            'event_id': 'evt-webhook-001',
            'event_type': 'bounce',
            'email': 'user@example.com',
            'tenant_id': 1,
        }, format='json')
        # Accepted and queued (task dispatched)
        assert resp.status_code == 200
        assert resp.data['queued'] is True

    def test_webhook_missing_event_id_rejected(self):
        c = APIClient()
        resp = c.post('/api/v1/communications/webhooks/deliverability/', {
            'event_type': 'bounce',
            'email': 'user@example.com',
        }, format='json')
        assert resp.status_code == 400
