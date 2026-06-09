"""
Tests for Customer Portal authentication.
Covers: login success, wrong credentials, platform staff rejection,
inactive account, portal_enabled=False rejection.
"""

import pytest
from rest_framework.test import APIClient

from apps.leads.models import Lead
from apps.tenants.models import Tenant
from apps.users.models import CustomerAccount, CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm Auth')


@pytest.fixture
def lead(tenant):
    return Lead.objects.create(
        tenant=tenant,
        first_name='Alice',
        last_name='Client',
        email='alice@client.com',
        status=Lead.STATUS_CLIENT,
        portal_enabled=True,
    )


@pytest.fixture
def customer_account(lead, tenant):
    return CustomerAccount.objects.create_user(
        email=lead.email,
        lead=lead,
        tenant=tenant,
        password='portalpass123!',
    )


@pytest.fixture
def platform_staff_user(db):
    return CustomUser.objects.create_user(
        email='staff@platform.com',
        password='staffpass123!',
        first_name='Super',
        last_name='Admin',
        role=CustomUser.ROLE_SUPER_ADMIN,
        user_type=CustomUser.TYPE_PLATFORM_STAFF,
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
class TestPortalLogin:

    def test_valid_login_returns_tokens_and_lead_info(self, api_client, customer_account, lead):
        resp = api_client.post('/api/v1/auth/portal/token/', {
            'email': 'alice@client.com',
            'password': 'portalpass123!',
        })
        assert resp.status_code == 200
        data = resp.json()
        assert 'access' in data
        assert 'refresh' in data
        assert str(data['lead_id']) == str(lead.pk)
        assert data['lead_status'] == Lead.STATUS_CLIENT
        assert data['user_type'] == 'customer'

    def test_wrong_password_returns_401(self, api_client, customer_account):
        resp = api_client.post('/api/v1/auth/portal/token/', {
            'email': 'alice@client.com',
            'password': 'wrongpassword',
        })
        assert resp.status_code == 401

    def test_missing_fields_returns_401(self, api_client, customer_account):
        resp = api_client.post('/api/v1/auth/portal/token/', {'email': 'alice@client.com'})
        assert resp.status_code == 401

    def test_platform_staff_rejected(self, api_client, platform_staff_user):
        """Authentication Matrix: platform staff MUST NOT log in via portal."""
        resp = api_client.post('/api/v1/auth/portal/token/', {
            'email': 'staff@platform.com',
            'password': 'staffpass123!',
        })
        assert resp.status_code == 401

    def test_inactive_account_rejected(self, api_client, customer_account):
        customer_account.is_active = False
        customer_account.save(update_fields=['is_active'])
        resp = api_client.post('/api/v1/auth/portal/token/', {
            'email': 'alice@client.com',
            'password': 'portalpass123!',
        })
        assert resp.status_code == 401

    def test_portal_disabled_rejected(self, api_client, customer_account, lead):
        lead.portal_enabled = False
        lead.save(update_fields=['portal_enabled'])
        resp = api_client.post('/api/v1/auth/portal/token/', {
            'email': 'alice@client.com',
            'password': 'portalpass123!',
        })
        assert resp.status_code == 401

    def test_nonexistent_email_returns_401(self, api_client, customer_account):
        resp = api_client.post('/api/v1/auth/portal/token/', {
            'email': 'nobody@nowhere.com',
            'password': 'portalpass123!',
        })
        assert resp.status_code == 401

    def test_tenant_employee_rejected(self, api_client, tenant):
        """Tenant employees must not log in via portal endpoint."""
        CustomUser.objects.create_user(
            email='advisor@firm.com',
            password='advisorpass!',
            first_name='Tom',
            last_name='Advisor',
            role=CustomUser.ROLE_ADVISOR,
            user_type=CustomUser.TYPE_TENANT_EMPLOYEE,
            tenant=tenant,
        )
        resp = api_client.post('/api/v1/auth/portal/token/', {
            'email': 'advisor@firm.com',
            'password': 'advisorpass!',
        })
        assert resp.status_code == 401
