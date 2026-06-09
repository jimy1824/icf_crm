"""
Tests for GET/POST /portal/consent/
BRU-07: once revoked, no automated messages until re-granted.
BRU-15: consent is append-only — each POST creates a new record.
BRU-33: audited.
"""

import pytest
from rest_framework.test import APIClient

from apps.leads.models import ConsentRecord, Lead
from apps.tenants.models import Tenant
from apps.users.models import CustomerAccount


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Consent Test Firm')


@pytest.fixture
def lead(tenant):
    return Lead.objects.create(
        tenant=tenant,
        first_name='Eve',
        last_name='Consent',
        email='eve@consent.com',
        status=Lead.STATUS_CLIENT,
        portal_enabled=True,
    )


@pytest.fixture
def customer_account(lead, tenant):
    return CustomerAccount.objects.create_user(
        email=lead.email, lead=lead, tenant=tenant, password='testpass123!'
    )


@pytest.fixture
def portal_client(customer_account):
    client = APIClient()
    client.force_authenticate(user=customer_account)
    return client


@pytest.fixture
def consent_record(lead, tenant):
    return ConsentRecord.objects.create(
        lead=lead,
        tenant=tenant,
        channel=ConsentRecord.CHANNEL_EMAIL,
        purpose='marketing',
        state=ConsentRecord.STATE_GRANTED,
        source='web_form',
    )


@pytest.mark.django_db
class TestPortalConsent:

    def test_list_consent_records(self, portal_client, consent_record):
        resp = portal_client.get('/api/v1/portal/consent/')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['channel'] == ConsentRecord.CHANNEL_EMAIL
        assert data[0]['state'] == ConsentRecord.STATE_GRANTED

    def test_post_consent_creates_new_record(self, portal_client, lead, tenant):
        """BRU-15: append-only — each POST creates a new record."""
        resp = portal_client.post('/api/v1/portal/consent/', {
            'channel': ConsentRecord.CHANNEL_SMS,
            'purpose': 'transactional',
            'state': ConsentRecord.STATE_GRANTED,
            'source': 'portal',
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data['channel'] == ConsentRecord.CHANNEL_SMS
        assert data['state'] == ConsentRecord.STATE_GRANTED

        assert ConsentRecord.objects.filter(lead=lead, tenant=tenant).count() == 1

    def test_revoke_consent_creates_new_record(self, portal_client, consent_record, lead, tenant):
        """BRU-07: revoking creates a new record (does NOT update existing)."""
        initial_count = ConsentRecord.objects.filter(lead=lead, tenant=tenant).count()
        resp = portal_client.post('/api/v1/portal/consent/', {
            'channel': ConsentRecord.CHANNEL_EMAIL,
            'purpose': 'marketing',
            'state': ConsentRecord.STATE_REVOKED,
            'source': 'portal_opt_out',
        })
        assert resp.status_code == 201
        new_count = ConsentRecord.objects.filter(lead=lead, tenant=tenant).count()
        assert new_count == initial_count + 1

        # The original record is untouched
        consent_record.refresh_from_db()
        assert consent_record.state == ConsentRecord.STATE_GRANTED

    def test_invalid_state_rejected(self, portal_client):
        resp = portal_client.post('/api/v1/portal/consent/', {
            'channel': ConsentRecord.CHANNEL_EMAIL,
            'purpose': 'marketing',
            'state': 'pending',  # pending not allowed from portal
            'source': 'portal',
        })
        assert resp.status_code == 400

    def test_cross_lead_isolation(self, portal_client, tenant):
        """BRU-01: portal user only sees their own consent records."""
        other_lead = Lead.objects.create(
            tenant=tenant,
            first_name='Frank',
            last_name='Other',
            email='frank@other.com',
            status=Lead.STATUS_CLIENT,
            portal_enabled=True,
        )
        ConsentRecord.objects.create(
            lead=other_lead,
            tenant=tenant,
            channel=ConsentRecord.CHANNEL_SMS,
            purpose='marketing',
            state=ConsentRecord.STATE_GRANTED,
            source='web_form',
        )
        resp = portal_client.get('/api/v1/portal/consent/')
        assert resp.status_code == 200
        # Should see empty (no records for our lead)
        assert resp.json() == []

    def test_unauthenticated_returns_403(self):
        client = APIClient()
        resp = client.get('/api/v1/portal/consent/')
        assert resp.status_code in (401, 403)
