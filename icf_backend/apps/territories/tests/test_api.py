"""
Territory API tests — CRUD, advisor assignment, analytics endpoints.
BRU-01: cross-tenant isolation verified at the API layer.
"""
import pytest
from rest_framework.test import APIClient

from apps.territories.models import Territory, AdvisorTerritory
from apps.territories.services import TerritoryService
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='API Firm')


@pytest.fixture
def other_tenant(db):
    return Tenant.objects.create(firm_name='Other Firm')


@pytest.fixture
def admin(db, tenant):
    return CustomUser.objects.create_user(
        email='admin@api.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_TENANT_ADMIN,
        first_name='Admin', last_name='API',
    )


@pytest.fixture
def advisor(db, tenant):
    return CustomUser.objects.create_user(
        email='advisor@api.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Adv', last_name='API',
    )


@pytest.fixture
def territory(db, tenant, admin):
    return TerritoryService.create_territory(
        tenant=tenant, name='API Territory', actor=admin,
    )


@pytest.fixture
def admin_client(admin):
    client = APIClient()
    client.force_authenticate(user=admin)
    return client


@pytest.fixture
def advisor_client(advisor):
    client = APIClient()
    client.force_authenticate(user=advisor)
    return client


@pytest.mark.django_db
class TestTerritoryListCreate:

    def test_list_returns_own_territories(self, admin_client, territory):
        resp = admin_client.get('/api/v1/territories/')
        assert resp.status_code == 200
        ids = [r['id'] for r in resp.data]
        assert territory.pk in ids

    def test_create_territory(self, admin_client):
        resp = admin_client.post('/api/v1/territories/', {'name': 'New Territory'})
        assert resp.status_code == 201
        assert resp.data['name'] == 'New Territory'

    def test_create_requires_tenant_admin(self, advisor_client):
        resp = advisor_client.post('/api/v1/territories/', {'name': 'X'})
        assert resp.status_code == 403

    def test_bru01_other_tenant_territories_not_visible(self, admin_client, other_tenant):
        other_admin = CustomUser.objects.create_user(
            email='admin@other.com', password='pass', tenant=other_tenant,
            role=CustomUser.ROLE_TENANT_ADMIN, first_name='X', last_name='Y',
        )
        other_t = TerritoryService.create_territory(
            tenant=other_tenant, name='Hidden', actor=other_admin,
        )
        resp = admin_client.get('/api/v1/territories/')
        ids = [r['id'] for r in resp.data]
        assert other_t.pk not in ids


@pytest.mark.django_db
class TestTerritoryDetail:

    def test_retrieve(self, admin_client, territory):
        resp = admin_client.get(f'/api/v1/territories/{territory.pk}/')
        assert resp.status_code == 200
        assert resp.data['name'] == territory.name

    def test_update(self, admin_client, territory):
        resp = admin_client.patch(
            f'/api/v1/territories/{territory.pk}/',
            {'name': 'Updated Name'},
        )
        assert resp.status_code == 200
        assert resp.data['name'] == 'Updated Name'

    def test_soft_delete(self, admin_client, territory):
        resp = admin_client.delete(f'/api/v1/territories/{territory.pk}/')
        assert resp.status_code == 204
        territory.refresh_from_db()
        assert territory.is_active is False

    def test_bru01_cannot_access_other_tenant_territory(self, admin_client, other_tenant):
        other_admin = CustomUser.objects.create_user(
            email='adm@other.com', password='pass', tenant=other_tenant,
            role=CustomUser.ROLE_TENANT_ADMIN, first_name='X', last_name='Y',
        )
        other_t = TerritoryService.create_territory(
            tenant=other_tenant, name='Secret', actor=other_admin,
        )
        resp = admin_client.get(f'/api/v1/territories/{other_t.pk}/')
        assert resp.status_code == 404


@pytest.mark.django_db
class TestAdvisorAssignmentAPI:

    def test_assign_advisor(self, admin_client, territory, advisor):
        resp = admin_client.post(
            f'/api/v1/territories/{territory.pk}/assign-advisor/',
            {'advisor_id': advisor.pk},
        )
        assert resp.status_code == 201
        assert AdvisorTerritory.objects.filter(advisor=advisor, territory=territory).exists()

    def test_list_advisors(self, admin_client, territory, advisor):
        TerritoryService.assign_advisor(
            territory=territory, advisor=advisor, actor=None,
        )
        resp = admin_client.get(f'/api/v1/territories/{territory.pk}/advisors/')
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_remove_advisor(self, admin_client, territory, advisor):
        TerritoryService.assign_advisor(territory=territory, advisor=advisor, actor=None)
        resp = admin_client.delete(
            f'/api/v1/territories/{territory.pk}/advisors/{advisor.pk}/',
        )
        assert resp.status_code == 204
        assert not AdvisorTerritory.objects.filter(advisor=advisor, territory=territory).exists()

    def test_list_advisor_territories(self, admin_client, territory, advisor):
        TerritoryService.assign_advisor(territory=territory, advisor=advisor, actor=None)
        resp = admin_client.get(f'/api/v1/territories/advisor/{advisor.pk}/')
        assert resp.status_code == 200
        ids = [r['id'] for r in resp.data]
        assert territory.pk in ids


@pytest.mark.django_db
class TestAnalyticsAPI:

    def test_summary_endpoint(self, admin_client, territory):
        resp = admin_client.get(f'/api/v1/territories/{territory.pk}/analytics/summary/')
        assert resp.status_code == 200
        assert 'total_leads' in resp.data
        assert 'active_advisors' in resp.data

    def test_weekly_endpoint(self, admin_client, territory):
        resp = admin_client.get(f'/api/v1/territories/{territory.pk}/analytics/weekly/')
        assert resp.status_code == 200
        assert 'week' in resp.data
        assert 'total_leads' in resp.data

    def test_advisor_analytics_endpoint(self, admin_client, advisor):
        resp = admin_client.get(f'/api/v1/territories/analytics/advisor/{advisor.pk}/')
        assert resp.status_code == 200
        assert 'territories' in resp.data

    def test_graph_leads_endpoint(self, admin_client):
        resp = admin_client.get('/api/v1/territories/analytics/graph/leads/')
        assert resp.status_code == 200
        assert isinstance(resp.data, list)

    def test_graph_advisors_endpoint(self, admin_client):
        resp = admin_client.get('/api/v1/territories/analytics/graph/advisors/')
        assert resp.status_code == 200

    def test_graph_weekly_trend_endpoint(self, admin_client):
        resp = admin_client.get('/api/v1/territories/analytics/graph/weekly-trend/')
        assert resp.status_code == 200

    def test_graph_campaigns_endpoint(self, admin_client):
        resp = admin_client.get('/api/v1/territories/analytics/graph/campaigns/')
        assert resp.status_code == 200

    def test_graph_conversion_endpoint(self, admin_client):
        resp = admin_client.get('/api/v1/territories/analytics/graph/conversion/')
        assert resp.status_code == 200
