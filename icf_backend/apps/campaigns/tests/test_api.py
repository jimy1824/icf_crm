"""
Campaign API tests.
BRU-01: tenant isolation.
BRU-03/07/09/17/21: lifecycle and enroll rules.
"""
import pytest
from rest_framework.test import APIClient

from apps.campaigns.models import Campaign, CampaignEnrollment, CampaignStep
from apps.campaigns.services import CampaignService
from apps.leads.models import Lead
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='API Firm')


@pytest.fixture
def advisor(tenant):
    return CustomUser.objects.create_user(
        email='api_adv@firm.com', password='pass1234!',
        first_name='A', last_name='B',
        role=CustomUser.ROLE_ADVISOR, tenant=tenant,
    )


@pytest.fixture
def team_lead(tenant):
    return CustomUser.objects.create_user(
        email='tl@firm.com', password='pass1234!',
        first_name='T', last_name='L',
        role=CustomUser.ROLE_TEAM_LEAD, tenant=tenant,
    )


@pytest.fixture
def lead(tenant):
    return Lead.objects.create(
        tenant=tenant, first_name='Lead', last_name='One',
        email='lead@example.com', source=Lead.SOURCE_MANUAL,
    )


@pytest.fixture
def auth_client(advisor):
    c = APIClient()
    c.force_authenticate(user=advisor)
    return c


@pytest.fixture
def tl_client(team_lead):
    c = APIClient()
    c.force_authenticate(user=team_lead)
    return c


@pytest.fixture
def campaign(tenant, advisor):
    return Campaign.objects.create(tenant=tenant, name='API Campaign', created_by=advisor)


@pytest.fixture
def active_campaign(tenant, advisor):
    c = Campaign.objects.create(tenant=tenant, name='Active Campaign', created_by=advisor)
    CampaignStep.objects.create(
        campaign=c, step_number=1,
        channel=CampaignStep.CHANNEL_EMAIL,
        content_template='Hello', delay_days=0,
    )
    return CampaignService.activate_campaign(campaign=c, actor=advisor)


@pytest.mark.django_db
class TestCampaignCRUD:

    def test_list_campaigns(self, auth_client, campaign):
        resp = auth_client.get('/api/v1/campaigns/')
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_create_campaign(self, auth_client):
        resp = auth_client.post('/api/v1/campaigns/', {
            'name': 'New Campaign',
            'steps': [{'channel': 'email', 'content_template': 'Hi', 'delay_days': 0}],
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['status'] == 'draft'

    def test_retrieve_campaign(self, auth_client, campaign):
        resp = auth_client.get(f'/api/v1/campaigns/{campaign.pk}/')
        assert resp.status_code == 200
        assert resp.data['name'] == 'API Campaign'

    def test_unauthenticated_blocked(self):
        c = APIClient()
        resp = c.get('/api/v1/campaigns/')
        assert resp.status_code == 401

    def test_bru_01_cross_tenant_campaign_not_visible(self, auth_client):
        t2 = Tenant.objects.create(firm_name='Other Firm')
        adv2 = CustomUser.objects.create_user(
            email='adv2@other.com', password='pass!',
            first_name='X', last_name='Y',
            role=CustomUser.ROLE_ADVISOR, tenant=t2,
        )
        Campaign.objects.create(tenant=t2, name='Hidden', created_by=adv2)
        resp = auth_client.get('/api/v1/campaigns/')
        names = [c['name'] for c in resp.data]
        assert 'Hidden' not in names


@pytest.mark.django_db
class TestCampaignActivation:

    def test_activate_campaign(self, tl_client, campaign):
        CampaignStep.objects.create(
            campaign=campaign, step_number=1,
            channel=CampaignStep.CHANNEL_EMAIL,
            content_template='Hi', delay_days=0,
        )
        resp = tl_client.post(f'/api/v1/campaigns/{campaign.pk}/activate/')
        assert resp.status_code == 200
        assert resp.data['status'] == 'active'

    def test_bru_09_activate_empty_campaign_rejected(self, tl_client, campaign):
        """BRU-09: cannot activate with no steps."""
        resp = tl_client.post(f'/api/v1/campaigns/{campaign.pk}/activate/')
        assert resp.status_code == 400

    def test_advisor_cannot_activate(self, auth_client, campaign):
        """Team lead or above required for activation."""
        CampaignStep.objects.create(
            campaign=campaign, step_number=1,
            channel=CampaignStep.CHANNEL_EMAIL,
            content_template='Hi', delay_days=0,
        )
        resp = auth_client.post(f'/api/v1/campaigns/{campaign.pk}/activate/')
        assert resp.status_code == 403

    def test_pause_active_campaign(self, tl_client, active_campaign):
        resp = tl_client.post(f'/api/v1/campaigns/{active_campaign.pk}/pause/')
        assert resp.status_code == 200
        assert resp.data['status'] == 'paused'


@pytest.mark.django_db
class TestCampaignEnrollAPI:

    def test_enroll_lead(self, auth_client, active_campaign, lead):
        resp = auth_client.post(
            f'/api/v1/campaigns/{active_campaign.pk}/enrollments/',
            {'lead_id': lead.pk},
            format='json',
        )
        assert resp.status_code == 201
        assert resp.data['status'] == 'active'

    def test_bru_07_opted_out_lead_rejected(self, auth_client, active_campaign, lead):
        """BRU-07: opted-out lead enrollment rejected."""
        lead.opted_out = True
        lead.save()
        resp = auth_client.post(
            f'/api/v1/campaigns/{active_campaign.pk}/enrollments/',
            {'lead_id': lead.pk},
            format='json',
        )
        assert resp.status_code == 400

    def test_bru_03_duplicate_enrollment_rejected(self, auth_client, active_campaign, lead):
        """BRU-03: second enrollment in same campaign rejected."""
        CampaignService.enroll_subject(campaign=active_campaign, actor=None, lead=lead)
        resp = auth_client.post(
            f'/api/v1/campaigns/{active_campaign.pk}/enrollments/',
            {'lead_id': lead.pk},
            format='json',
        )
        assert resp.status_code == 400

    def test_stop_enrollment(self, auth_client, active_campaign, lead, advisor):
        enrollment = CampaignService.enroll_subject(
            campaign=active_campaign, actor=advisor, lead=lead,
        )
        resp = auth_client.post(
            f'/api/v1/campaigns/enrollments/{enrollment.pk}/stop/',
            {'reason': 'manual'},
            format='json',
        )
        assert resp.status_code == 200
        assert resp.data['status'] == 'stopped'

    def test_bru_21_stop_already_stopped_rejected(self, auth_client, active_campaign, lead, advisor):
        """BRU-21: stopping an already-stopped enrollment fails."""
        enrollment = CampaignService.enroll_subject(
            campaign=active_campaign, actor=advisor, lead=lead,
        )
        CampaignService.stop_enrollment(
            enrollment=enrollment, actor=advisor, reason='manual',
        )
        resp = auth_client.post(
            f'/api/v1/campaigns/enrollments/{enrollment.pk}/stop/',
            {'reason': 'manual'},
            format='json',
        )
        assert resp.status_code == 400
