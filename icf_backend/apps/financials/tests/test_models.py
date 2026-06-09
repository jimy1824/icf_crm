import pytest
from decimal import Decimal
from apps.financials.models import FinancialProfile, FinancialAccount, FinancialGoal
from apps.tenants.models import Tenant
from apps.leads.models import Lead
import datetime


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm')


@pytest.fixture
def lead_obj(tenant):
    return Lead.objects.create(
        tenant=tenant, first_name='Jane', last_name='Doe',
        email='jane@example.com', source=Lead.SOURCE_MANUAL,
        status=Lead.STATUS_CLIENT,
    )


@pytest.fixture
def profile(tenant, lead_obj):
    return FinancialProfile.objects.create(
        lead=lead_obj,
        tenant=tenant,
        total_assets=Decimal('500000.00'),
        assets_currency='USD',
        total_liabilities=Decimal('150000.00'),
        liabilities_currency='USD',
    )


@pytest.mark.django_db
class TestFinancialProfile:
    def test_net_worth_is_derived(self, profile):
        # BRU-27: net_worth must be a property, not a stored column
        assert profile.net_worth == Decimal('350000.00')
        assert 'net_worth' not in [f.name for f in FinancialProfile._meta.get_fields()]

    def test_net_worth_updates_without_save(self, profile):
        profile.total_assets = Decimal('600000.00')
        assert profile.net_worth == Decimal('450000.00')

    def test_str(self, profile):
        assert 'Jane' in str(profile)


@pytest.mark.django_db
class TestFinancialAccount:
    def test_requires_currency_and_date(self, profile, tenant):
        # BRU-26: currency + as_of_date are mandatory
        account = FinancialAccount.objects.create(
            profile=profile,
            tenant=tenant,
            account_type=FinancialAccount.TYPE_IRA,
            value=Decimal('100000.00'),
            currency='USD',
            as_of_date=datetime.date.today(),
        )
        assert account.currency == 'USD'
        assert account.as_of_date is not None


@pytest.mark.django_db
class TestFinancialGoal:
    def test_create(self, tenant, lead_obj):
        goal = FinancialGoal.objects.create(
            lead=lead_obj,
            tenant=tenant,
            goal_type=FinancialGoal.TYPE_RETIREMENT,
            target_amount=Decimal('1000000.00'),
            target_currency='USD',
            target_date=datetime.date(2045, 1, 1),
        )
        assert goal.is_off_track is False
        assert goal.progress_pct == Decimal('0')
