"""
Tests for FM-12/FM-26: Analytics service.
BRU-01: tenant isolation in dashboard aggregations.
"""
import datetime
import pytest

from apps.analytics.models import AnalyticsSnapshot
from apps.analytics.services import AnalyticsService
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Firm A')


@pytest.fixture
def other_tenant(db):
    return Tenant.objects.create(firm_name='Firm B')


@pytest.fixture
def advisor(db, tenant):
    return CustomUser.objects.create_user(
        email='advisor@firm.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Alex', last_name='Advisor',
    )


@pytest.mark.django_db
class TestFirmDashboard:

    def test_returns_expected_keys(self, tenant):
        data = AnalyticsService.firm_dashboard(tenant=tenant)
        assert 'leads' in data
        assert 'campaigns' in data
        assert 'communications' in data

    def test_zero_leads_gives_zero_conversion_rate(self, tenant):
        data = AnalyticsService.firm_dashboard(tenant=tenant)
        assert data['leads']['total'] == 0
        assert data['leads']['conversion_rate_pct'] == 0.0

    def test_bru01_only_counts_own_tenant_leads(self, tenant, other_tenant):
        from apps.leads.models import Lead
        Lead.objects.create(
            tenant=other_tenant, first_name='X', last_name='Y',
            email='x@y.com', status=Lead.STATUS_LEAD,
        )
        data = AnalyticsService.firm_dashboard(tenant=tenant)
        assert data['leads']['total'] == 0


@pytest.mark.django_db
class TestAdvisorDashboard:

    def test_returns_expected_keys(self, tenant, advisor):
        data = AnalyticsService.advisor_dashboard(tenant=tenant, advisor=advisor)
        assert 'my_leads' in data
        assert 'my_clients' in data
        assert 'communications_last_30_days' in data
        assert 'upcoming_meetings' in data

    def test_counts_only_own_leads(self, tenant, advisor):
        from apps.leads.models import Lead
        other = CustomUser.objects.create_user(
            email='other@firm.com', password='pass',
            tenant=tenant, role=CustomUser.ROLE_ADVISOR,
            first_name='B', last_name='B',
        )
        lead = Lead.objects.create(
            tenant=tenant, first_name='A', last_name='B',
            email='a@b.com', status=Lead.STATUS_LEAD,
        )
        lead.assigned_advisors.add(advisor)
        other_lead = Lead.objects.create(
            tenant=tenant, first_name='C', last_name='D',
            email='c@d.com', status=Lead.STATUS_LEAD,
        )
        other_lead.assigned_advisors.add(other)
        data = AnalyticsService.advisor_dashboard(tenant=tenant, advisor=advisor)
        assert data['my_leads'] == 1


@pytest.mark.django_db
class TestFirmSnapshot:

    def test_snapshot_created(self, tenant):
        snapshot = AnalyticsService.take_firm_snapshot(tenant=tenant)
        assert snapshot.pk is not None
        assert snapshot.level == AnalyticsSnapshot.LEVEL_FIRM
        assert snapshot.tenant == tenant

    def test_snapshot_idempotent(self, tenant):
        today = datetime.date.today()
        s1 = AnalyticsService.take_firm_snapshot(tenant=tenant, snapshot_date=today)
        s2 = AnalyticsService.take_firm_snapshot(tenant=tenant, snapshot_date=today)
        assert s1.pk == s2.pk  # update_or_create → same row

    def test_snapshot_bru01_scoped_to_tenant(self, tenant, other_tenant):
        s1 = AnalyticsService.take_firm_snapshot(tenant=tenant)
        s2 = AnalyticsService.take_firm_snapshot(tenant=other_tenant)
        assert s1.tenant == tenant
        assert s2.tenant == other_tenant
        assert s1.pk != s2.pk


@pytest.mark.django_db
class TestAdvisorSnapshot:

    def test_advisor_snapshot_created(self, tenant, advisor):
        snapshot = AnalyticsService.take_advisor_snapshot(tenant=tenant, advisor=advisor)
        assert snapshot.level == AnalyticsSnapshot.LEVEL_ADVISOR
        assert snapshot.entity_id == str(advisor.pk)

    def test_advisor_snapshot_idempotent(self, tenant, advisor):
        today = datetime.date.today()
        s1 = AnalyticsService.take_advisor_snapshot(
            tenant=tenant, advisor=advisor, snapshot_date=today,
        )
        s2 = AnalyticsService.take_advisor_snapshot(
            tenant=tenant, advisor=advisor, snapshot_date=today,
        )
        assert s1.pk == s2.pk
