"""
Tests for GET/PATCH /portal/me/
"""

import pytest
from rest_framework.test import APIClient

from apps.leads.models import Lead
from apps.portal.authentication import CustomerJWTAuthentication
from apps.tenants.models import Tenant
from apps.users.models import CustomerAccount


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Me Test Firm')


@pytest.fixture
def lead(tenant):
    return Lead.objects.create(
        tenant=tenant,
        first_name='Bob',
        last_name='Portal',
        email='bob@portal.com',
        status=Lead.STATUS_CLIENT,
        portal_enabled=True,
        phone='555-1234',
        preferred_timezone='America/New_York',
    )


@pytest.fixture
def customer_account(lead, tenant):
    return CustomerAccount.objects.create_user(
        email=lead.email,
        lead=lead,
        tenant=tenant,
        password='testpass123!',
    )


@pytest.fixture
def portal_client(customer_account):
    client = APIClient()
    client.force_authenticate(user=customer_account, token=None)
    return client


@pytest.mark.django_db
class TestPortalMe:

    def test_get_me_returns_lead_profile(self, portal_client, customer_account, lead):
        resp = portal_client.get('/api/v1/portal/me/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['email'] == lead.email
        assert data['user_type'] == 'customer'
        assert data['lead']['first_name'] == lead.first_name
        assert data['lead']['email'] == lead.email
        assert data['lead']['status'] == Lead.STATUS_CLIENT

    def test_patch_me_updates_phone_and_timezone(self, portal_client, lead):
        resp = portal_client.patch('/api/v1/portal/me/', {
            'phone': '555-9999',
            'preferred_timezone': 'America/Chicago',
        })
        assert resp.status_code == 200
        lead.refresh_from_db()
        assert lead.phone == '555-9999'
        assert lead.preferred_timezone == 'America/Chicago'

    def test_patch_me_cannot_change_status(self, portal_client, lead):
        """BRU-14: status is NOT writable by portal users."""
        resp = portal_client.patch('/api/v1/portal/me/', {'status': Lead.STATUS_FORMER_CLIENT})
        assert resp.status_code == 200
        lead.refresh_from_db()
        # Status should be unchanged
        assert lead.status == Lead.STATUS_CLIENT

    def test_patch_me_cannot_change_email(self, portal_client, lead):
        """BRU-14: email is NOT writable by portal users."""
        resp = portal_client.patch('/api/v1/portal/me/', {'email': 'hacked@evil.com'})
        assert resp.status_code == 200
        lead.refresh_from_db()
        assert lead.email == 'bob@portal.com'

    def test_unauthenticated_returns_403(self):
        client = APIClient()
        resp = client.get('/api/v1/portal/me/')
        assert resp.status_code in (401, 403)

    def test_cross_lead_isolation(self, portal_client, tenant):
        """BRU-01: portal user can only see their own lead, not another's."""
        other_lead = Lead.objects.create(
            tenant=tenant,
            first_name='Eve',
            last_name='Other',
            email='eve@other.com',
            status=Lead.STATUS_CLIENT,
            portal_enabled=True,
        )
        # Attempt to read me — should return THIS user's data, not other_lead's
        resp = portal_client.get('/api/v1/portal/me/')
        assert resp.status_code == 200
        assert resp.json()['lead']['email'] != other_lead.email
