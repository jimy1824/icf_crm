import pytest
from rest_framework.test import APIClient

from apps.leads.models import Lead, KanbanCard, ActivityNote
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Acme Advisors')


@pytest.fixture
def other_tenant(db):
    return Tenant.objects.create(firm_name='Other Firm')


@pytest.fixture
def advisor(tenant):
    return CustomUser.objects.create_user(
        email='advisor@acme.com', password='pass1234!',
        first_name='Jane', last_name='Advisor',
        role=CustomUser.ROLE_ADVISOR, tenant=tenant,
    )


@pytest.fixture
def team_lead(tenant):
    return CustomUser.objects.create_user(
        email='lead@acme.com', password='pass1234!',
        first_name='Tom', last_name='Lead',
        role=CustomUser.ROLE_TEAM_LEAD, tenant=tenant,
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client, advisor):
    api_client.force_authenticate(user=advisor)
    return api_client


@pytest.fixture
def lead_client(api_client, team_lead):
    api_client.force_authenticate(user=team_lead)
    return api_client


@pytest.fixture
def lead(tenant, advisor):
    from apps.leads.services import LeadService
    return LeadService.create_lead(
        tenant=tenant, first_name='Bob', last_name='Test',
        email='bob@test.com', actor=advisor,
    )


@pytest.mark.django_db
class TestLeadCreate:

    def test_create_lead(self, auth_client, advisor):
        """FR-08.1: manual lead creation returns 201."""
        resp = auth_client.post('/api/v1/leads/', {
            'first_name': 'Alice', 'last_name': 'Smith',
            'email': 'alice@test.com', 'source': 'manual',
        })
        assert resp.status_code == 201

    def test_create_lead_idempotent(self, auth_client, lead):
        """BRU-16: posting the same email twice returns the existing lead, not 400."""
        resp = auth_client.post('/api/v1/leads/', {
            'first_name': 'Different', 'last_name': 'Name',
            'email': lead.email, 'source': 'manual',
        })
        assert resp.status_code == 201
        assert Lead.objects.filter(tenant=lead.tenant, email=lead.email).count() == 1

    def test_unauthenticated_rejected(self, api_client):
        resp = api_client.post('/api/v1/leads/', {
            'first_name': 'X', 'last_name': 'Y', 'email': 'x@test.com',
        })
        assert resp.status_code == 401


@pytest.mark.django_db
class TestTenantIsolation:

    def test_cannot_read_other_tenants_leads(self, db, api_client):
        """BRU-01: advisor from Firm A must never see Firm B leads."""
        firm_a = Tenant.objects.create(firm_name='Firm A')
        firm_b = Tenant.objects.create(firm_name='Firm B')
        advisor_a = CustomUser.objects.create_user(
            email='a@firma.com', password='pass1234!',
            first_name='A', last_name='A',
            role=CustomUser.ROLE_ADVISOR, tenant=firm_a,
        )
        Lead.objects.create(
            tenant=firm_b, first_name='Secret', last_name='Lead',
            email='secret@firmb.com', source=Lead.SOURCE_MANUAL,
            pipeline_stage=Lead.STAGE_NEW, status=Lead.STATUS_LEAD,
        )
        api_client.force_authenticate(user=advisor_a)
        resp = api_client.get('/api/v1/leads/')
        assert resp.status_code == 200
        emails = [l['email'] for l in resp.data['results']]
        assert 'secret@firmb.com' not in emails


@pytest.mark.django_db
class TestLeadAssign:

    def test_assign_advisor(self, lead_client, lead, team_lead, advisor):
        """FR-08.3 / BRU-06: successful advisor assignment."""
        resp = lead_client.post(f'/api/v1/leads/{lead.pk}/assign/', {
            'advisor_ids': [advisor.pk],
        }, format='json')
        assert resp.status_code == 200

    def test_assign_requires_team_lead_or_above(self, auth_client, lead, advisor):
        """Only team_lead or above can assign (permission check)."""
        resp = auth_client.post(f'/api/v1/leads/{lead.pk}/assign/', {
            'advisor_ids': [advisor.pk],
        }, format='json')
        assert resp.status_code == 403


@pytest.mark.django_db
class TestMoveStage:

    def test_move_stage(self, lead_client, lead):
        """BRU-31: stage move returns 200 with updated lead."""
        resp = lead_client.post(f'/api/v1/leads/{lead.pk}/move-stage/', {
            'stage': Lead.STAGE_CONTACTED, 'position': 0,
        }, format='json')
        assert resp.status_code == 200
        assert resp.data['pipeline_stage'] == Lead.STAGE_CONTACTED

    def test_invalid_stage_returns_400(self, lead_client, lead):
        resp = lead_client.post(f'/api/v1/leads/{lead.pk}/move-stage/', {
            'stage': 'not_a_real_stage',
        }, format='json')
        assert resp.status_code == 400


@pytest.mark.django_db
class TestTimeline:

    def test_add_private_note(self, auth_client, lead, advisor):
        """BRU-12: can add a private note via the timeline endpoint."""
        resp = auth_client.post(f'/api/v1/leads/{lead.pk}/timeline/', {
            'body': 'Internal note.', 'is_private': True,
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['is_private'] is True

    def test_client_role_cannot_see_private_notes(self, db, api_client, lead, tenant):
        """BRU-08: customer portal users are denied access to the Tenant CRM lead timeline entirely."""
        from apps.users.models import CustomUser
        client_user = CustomUser.objects.create_user(
            email='client@test.com', password='pass1234!',
            first_name='Client', last_name='User',
            role=CustomUser.ROLE_ADVISOR, tenant=tenant,
            user_type=CustomUser.TYPE_CUSTOMER,
        )
        api_client.force_authenticate(user=client_user)
        resp = api_client.get(f'/api/v1/leads/{lead.pk}/timeline/')
        # BRU-08: customer portal users are blocked at the permission layer
        assert resp.status_code in (403, 401)

    def test_advisor_sees_private_notes(self, auth_client, lead, advisor):
        """Advisors must see private notes in their own tenant's timeline."""
        from apps.leads.services import LeadService
        LeadService.add_note(
            tenant=lead.tenant, lead=lead, author=advisor,
            body='Secret.', is_private=True,
        )
        resp = auth_client.get(f'/api/v1/leads/{lead.pk}/timeline/')
        assert resp.status_code == 200
        private_notes = [n for n in resp.data if n['is_private']]
        assert len(private_notes) > 0


@pytest.mark.django_db
class TestKanbanBoard:

    def test_kanban_returns_active_leads(self, auth_client, lead):
        resp = auth_client.get('/api/v1/leads/kanban/')
        assert resp.status_code == 200

    def test_closed_won_excluded_from_kanban(self, auth_client, lead):
        """Closed Won leads should not appear on the active kanban board."""
        from apps.leads.services import LeadService
        LeadService.move_stage(lead=lead, new_stage=Lead.STAGE_CLOSED_WON)
        resp = auth_client.get('/api/v1/leads/kanban/')
        assert resp.status_code == 200
        pks = [l['id'] for l in resp.data]
        assert lead.pk not in pks
