import datetime
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.financials.models import (
    CalculatorResult,
    FinancialAccount,
    FinancialGoal,
    FinancialProfile,
)
from apps.financials.services import FinancialProfileService, GoalService
from apps.leads.models import Lead
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Acme Advisors')


@pytest.fixture
def advisor(tenant):
    return CustomUser.objects.create_user(
        email='advisor@acme.com', password='pass1234!',
        first_name='Jane', last_name='Advisor',
        role=CustomUser.ROLE_ADVISOR, tenant=tenant,
    )


@pytest.fixture
def lead_obj(tenant):
    return Lead.objects.create(
        tenant=tenant, first_name='Bob', last_name='Client',
        email='bob@test.com', source=Lead.SOURCE_MANUAL,
        status=Lead.STATUS_CLIENT,
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client, advisor):
    api_client.force_authenticate(user=advisor)
    return api_client


@pytest.fixture
def profile(tenant, lead_obj, advisor):
    return FinancialProfileService.get_or_create_profile(
        tenant=tenant, lead=lead_obj, actor=advisor
    )


@pytest.fixture
def goal(tenant, lead_obj, advisor):
    return GoalService.create_goal(
        tenant=tenant, lead=lead_obj, actor=advisor,
        goal_type=FinancialGoal.TYPE_RETIREMENT,
        target_amount=Decimal('1000000'),
        target_currency='USD',
        target_date=datetime.date(2050, 1, 1),
    )


# ---------------------------------------------------------------------------
# Financial Profile API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestFinancialProfileAPI:

    def test_retrieve_profile(self, auth_client, profile, lead_obj):
        url = f'/api/v1/financials/leads/{lead_obj.pk}/financial-profile/'
        resp = auth_client.get(url)
        assert resp.status_code == 200
        assert 'net_worth' in resp.data

    def test_retrieve_no_profile_returns_404(self, auth_client, lead_obj):
        url = f'/api/v1/financials/leads/{lead_obj.pk}/financial-profile/'
        resp = auth_client.get(url)
        assert resp.status_code == 404

    def test_patch_profile_income(self, auth_client, profile, lead_obj):
        url = f'/api/v1/financials/leads/{lead_obj.pk}/financial-profile/'
        resp = auth_client.patch(url, {
            'annual_income': '120000.00',
            'income_currency': 'USD',
            'income_as_of': '2026-01-01',
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['annual_income'] == '120000.00'

    def test_unauthenticated_rejected(self, api_client, lead_obj):
        url = f'/api/v1/financials/leads/{lead_obj.pk}/financial-profile/'
        resp = api_client.get(url)
        assert resp.status_code == 401

    def test_add_account(self, auth_client, profile, lead_obj):
        url = f'/api/v1/financials/leads/{lead_obj.pk}/financial-profile/accounts/add/'
        resp = auth_client.post(url, {
            'account_type': 'ira',
            'value': '200000.00',
            'currency': 'USD',
            'as_of_date': '2026-01-01',
        }, format='json')
        assert resp.status_code == 201
        assert FinancialAccount.objects.filter(profile=profile).count() == 1

    def test_list_accounts(self, auth_client, profile, lead_obj, advisor):
        FinancialProfileService.add_account(
            profile=profile, actor=advisor,
            account_type=FinancialAccount.TYPE_BROKERAGE,
            value=Decimal('100000'), currency='USD',
            as_of_date=datetime.date.today(),
        )
        url = f'/api/v1/financials/leads/{lead_obj.pk}/financial-profile/accounts/'
        resp = auth_client.get(url)
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_bru_01_cross_tenant_profile_inaccessible(self, api_client):
        """BRU-01: advisor from Firm A cannot access Firm B's lead profile."""
        t1 = Tenant.objects.create(firm_name='Firm A')
        t2 = Tenant.objects.create(firm_name='Firm B')
        advisor_a = CustomUser.objects.create_user(
            email='a@firma.com', password='pass1234!',
            first_name='A', last_name='A',
            role=CustomUser.ROLE_ADVISOR, tenant=t1,
        )
        lead_b = Lead.objects.create(
            tenant=t2, first_name='B', last_name='B',
            email='b@firmb.com', source=Lead.SOURCE_MANUAL,
            status=Lead.STATUS_CLIENT,
        )
        api_client.force_authenticate(user=advisor_a)
        url = f'/api/v1/financials/leads/{lead_b.pk}/financial-profile/'
        resp = api_client.get(url)
        # Either 404 (correct — lead not found in tenant) or 403
        assert resp.status_code in [403, 404]


# ---------------------------------------------------------------------------
# Goals API
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGoalsAPI:

    def test_list_goals(self, auth_client, goal, lead_obj):
        url = f'/api/v1/financials/leads/{lead_obj.pk}/goals/'
        resp = auth_client.get(url)
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_create_goal(self, auth_client, lead_obj):
        url = f'/api/v1/financials/leads/{lead_obj.pk}/goals/'
        resp = auth_client.post(url, {
            'goal_type': 'retirement',
            'target_amount': '500000.00',
            'target_currency': 'USD',
            'target_date': '2045-01-01',
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['goal_type'] == 'retirement'

    def test_retrieve_goal(self, auth_client, goal, lead_obj):
        url = f'/api/v1/financials/leads/{lead_obj.pk}/goals/{goal.pk}/'
        resp = auth_client.get(url)
        assert resp.status_code == 200

    def test_patch_goal(self, auth_client, goal, lead_obj):
        url = f'/api/v1/financials/leads/{lead_obj.pk}/goals/{goal.pk}/'
        resp = auth_client.patch(url, {'current_value': '250000.00'}, format='json')
        assert resp.status_code == 200
        assert resp.data['progress_pct'] == '25.00'

    def test_delete_goal(self, auth_client, goal, lead_obj):
        url = f'/api/v1/financials/leads/{lead_obj.pk}/goals/{goal.pk}/'
        resp = auth_client.delete(url)
        assert resp.status_code == 204
        assert not FinancialGoal.objects.filter(pk=goal.pk).exists()

    def test_add_milestone(self, auth_client, goal, lead_obj):
        url = f'/api/v1/financials/leads/{lead_obj.pk}/goals/{goal.pk}/milestones/'
        resp = auth_client.post(url, {
            'title': 'Halfway',
            'target_amount': '500000',
            'target_date': '2035-01-01',
        }, format='json')
        assert resp.status_code == 201


# ---------------------------------------------------------------------------
# Calculator API (FM-21)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCalculatorAPI:

    def test_run_retirement_calculator(self, auth_client):
        resp = auth_client.post('/api/v1/financials/calculators/', {
            'calculator_type': 'retirement',
            'inputs': {
                'current_age': 30, 'retirement_age': 65,
                'current_savings': 0, 'annual_contribution': 12000,
                'annual_return_pct': 7,
            },
        }, format='json')
        assert resp.status_code == 201
        assert 'projected_savings' in resp.data['outputs']

    def test_bru_34_disclaimer_in_response(self, auth_client):
        """BRU-34: disclaimer field must always be in the API response."""
        resp = auth_client.post('/api/v1/financials/calculators/', {
            'calculator_type': 'net_worth',
            'inputs': {'total_assets': 0, 'total_liabilities': 0},
        }, format='json')
        assert resp.status_code == 201
        assert 'disclaimer' in resp.data

    def test_bru_39_inputs_in_response(self, auth_client):
        """BRU-39: input set must be echoed back in the response."""
        inputs = {'total_assets': 100000, 'total_liabilities': 50000}
        resp = auth_client.post('/api/v1/financials/calculators/', {
            'calculator_type': 'net_worth',
            'inputs': inputs,
        }, format='json')
        assert resp.data['inputs'] == inputs

    def test_list_calculator_history(self, auth_client, tenant, advisor):
        from apps.financials.services import CalculatorService
        CalculatorService.run(
            tenant=tenant, run_by=advisor,
            calculator_type=CalculatorResult.CALC_NET_WORTH,
            inputs={'total_assets': 0, 'total_liabilities': 0},
        )
        resp = auth_client.get('/api/v1/financials/calculators/')
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_invalid_calculator_type_returns_400(self, auth_client):
        resp = auth_client.post('/api/v1/financials/calculators/', {
            'calculator_type': 'not_real',
            'inputs': {},
        }, format='json')
        assert resp.status_code == 400

    def test_unauthenticated_rejected(self, api_client):
        resp = api_client.post('/api/v1/financials/calculators/', {
            'calculator_type': 'net_worth',
            'inputs': {'total_assets': 0, 'total_liabilities': 0},
        }, format='json')
        assert resp.status_code == 401
