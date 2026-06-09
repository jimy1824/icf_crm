"""
Tests for FM-22: Global search service.
BRU-35: results filtered by role and tenant before return.
BRU-01: no cross-tenant leakage.
"""
import pytest

from apps.search.services import GlobalSearchService
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Alpha Advisors')


@pytest.fixture
def other_tenant(db):
    return Tenant.objects.create(firm_name='Beta Advisors')


@pytest.fixture
def admin_user(db, tenant):
    return CustomUser.objects.create_user(
        email='admin@alpha.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_TENANT_ADMIN,
        first_name='Admin', last_name='User',
    )


@pytest.fixture
def advisor_user(db, tenant):
    return CustomUser.objects.create_user(
        email='advisor@alpha.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Alice', last_name='Advisor',
    )


@pytest.fixture
def client_user(db, tenant):
    return CustomUser.objects.create_user(
        email='client@alpha.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        user_type=CustomUser.TYPE_CUSTOMER,
        first_name='Chris', last_name='Client',
    )


@pytest.fixture
def lead(db, tenant):
    from apps.leads.models import Lead
    return Lead.objects.create(
        tenant=tenant,
        first_name='John',
        last_name='Smith',
        email='john.smith@example.com',
        status=Lead.STATUS_LEAD,
    )


@pytest.fixture
def other_tenant_lead(db, other_tenant):
    from apps.leads.models import Lead
    return Lead.objects.create(
        tenant=other_tenant,
        first_name='John',
        last_name='Smith',
        email='john@other.com',
        status=Lead.STATUS_LEAD,
    )


@pytest.mark.django_db
class TestGlobalSearchService:

    def test_returns_empty_for_short_query(self, admin_user, tenant):
        results = GlobalSearchService.search(tenant=tenant, user=admin_user, query='j')
        assert results == []

    def test_returns_empty_for_blank_query(self, admin_user, tenant):
        results = GlobalSearchService.search(tenant=tenant, user=admin_user, query='')
        assert results == []

    def test_lead_found_by_first_name(self, lead, admin_user, tenant):
        results = GlobalSearchService.search(tenant=tenant, user=admin_user, query='John')
        types = [r.entity_type for r in results]
        assert 'lead' in types

    def test_lead_found_by_email(self, lead, admin_user, tenant):
        results = GlobalSearchService.search(tenant=tenant, user=admin_user, query='john.smith')
        types = [r.entity_type for r in results]
        assert 'lead' in types

    def test_bru01_no_cross_tenant_leakage(self, lead, other_tenant_lead, admin_user, tenant):
        """BRU-01: searching Tenant A must never return Tenant B data."""
        results = GlobalSearchService.search(tenant=tenant, user=admin_user, query='John')
        ids = [(r.entity_type, r.entity_id) for r in results]
        assert ('lead', lead.pk) in ids
        assert ('lead', other_tenant_lead.pk) not in ids

    def test_bru35_client_user_cannot_see_campaigns(self, client_user, tenant):
        """BRU-35: client role never receives campaign results."""
        from apps.campaigns.models import Campaign
        Campaign.objects.create(
            tenant=tenant, name='Campaign Alpha', status=Campaign.STATUS_ACTIVE,
            created_by=client_user,
        )
        results = GlobalSearchService.search(tenant=tenant, user=client_user, query='Alpha')
        types = [r.entity_type for r in results]
        assert 'campaign' not in types

    def test_bru35_client_user_cannot_see_communications(self, client_user, tenant):
        """BRU-35: client role never receives communication results."""
        results = GlobalSearchService.search(
            tenant=tenant, user=client_user, query='meeting',
        )
        types = [r.entity_type for r in results]
        assert 'communication' not in types

    def test_campaign_found_by_admin(self, admin_user, tenant):
        from apps.campaigns.models import Campaign
        c = Campaign.objects.create(
            tenant=tenant, name='Onboarding Flow', status=Campaign.STATUS_ACTIVE,
            created_by=admin_user,
        )
        results = GlobalSearchService.search(tenant=tenant, user=admin_user, query='Onboarding')
        types = [r.entity_type for r in results]
        assert 'campaign' in types

    def test_result_limit_respected(self, admin_user, tenant):
        from apps.leads.models import Lead
        for i in range(30):
            Lead.objects.create(
                tenant=tenant, first_name='SearchTarget', last_name=f'L{i}',
                email=f'st{i}@x.com', status=Lead.STATUS_LEAD,
            )
        results = GlobalSearchService.search(
            tenant=tenant, user=admin_user, query='SearchTarget', limit=10,
        )
        assert len(results) <= 10
