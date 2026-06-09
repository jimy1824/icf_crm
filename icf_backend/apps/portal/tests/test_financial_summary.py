"""
Tests for GET /portal/financial-summary/
BRU-14: financial profile is read-only.
BRU-01: only own profile visible.
"""

from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.financials.models import FinancialProfile
from apps.leads.models import Lead
from apps.tenants.models import Tenant
from apps.users.models import CustomerAccount


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Financial Test Firm')


@pytest.fixture
def lead(tenant):
    return Lead.objects.create(
        tenant=tenant,
        first_name='Carol',
        last_name='Client',
        email='carol@client.com',
        status=Lead.STATUS_CLIENT,
        portal_enabled=True,
    )


@pytest.fixture
def customer_account(lead, tenant):
    return CustomerAccount.objects.create_user(
        email=lead.email, lead=lead, tenant=tenant, password='testpass123!'
    )


@pytest.fixture
def financial_profile(lead, tenant):
    return FinancialProfile.objects.create(
        lead=lead,
        tenant=tenant,
        annual_income=Decimal('120000.00'),
        income_currency='USD',
        total_assets=Decimal('500000.00'),
        assets_currency='USD',
        total_liabilities=Decimal('100000.00'),
        liabilities_currency='USD',
        risk_tolerance=FinancialProfile.RISK_MODERATE,
    )


@pytest.fixture
def portal_client(customer_account):
    client = APIClient()
    client.force_authenticate(user=customer_account)
    return client


@pytest.mark.django_db
class TestPortalFinancialSummary:

    def test_returns_financial_profile(self, portal_client, financial_profile):
        resp = portal_client.get('/api/v1/portal/financial-summary/')
        assert resp.status_code == 200
        data = resp.json()
        assert data['annual_income'] == '120000.00'
        assert data['total_assets'] == '500000.00'
        assert data['risk_tolerance'] == FinancialProfile.RISK_MODERATE

    def test_net_worth_is_derived(self, portal_client, financial_profile):
        """BRU-27: net_worth = assets - liabilities, never stored."""
        resp = portal_client.get('/api/v1/portal/financial-summary/')
        data = resp.json()
        expected_nw = Decimal('500000.00') - Decimal('100000.00')
        assert Decimal(data['net_worth']) == expected_nw

    def test_no_profile_returns_404(self, portal_client, lead):
        resp = portal_client.get('/api/v1/portal/financial-summary/')
        assert resp.status_code == 404

    def test_cross_tenant_isolation(self, tenant, financial_profile):
        """BRU-01: another tenant's financial data is not accessible."""
        other_tenant = Tenant.objects.create(firm_name='Other Firm')
        other_lead = Lead.objects.create(
            tenant=other_tenant,
            first_name='Dan',
            last_name='Other',
            email='dan@other.com',
            status=Lead.STATUS_CLIENT,
            portal_enabled=True,
        )
        other_account = CustomerAccount.objects.create_user(
            email=other_lead.email,
            lead=other_lead,
            tenant=other_tenant,
            password='testpass123!',
        )
        other_client = APIClient()
        other_client.force_authenticate(user=other_account)

        # other tenant has no financial profile — gets 404, not the first tenant's data
        resp = other_client.get('/api/v1/portal/financial-summary/')
        assert resp.status_code == 404

    def test_unauthenticated_returns_403(self):
        client = APIClient()
        resp = client.get('/api/v1/portal/financial-summary/')
        assert resp.status_code in (401, 403)
