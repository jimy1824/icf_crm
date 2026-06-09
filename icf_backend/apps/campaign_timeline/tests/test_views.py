"""
API view tests for Campaign Timeline and Timezone endpoints.
"""
import datetime

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.campaigns.models import Campaign, CampaignEnrollment, CampaignStep
from apps.leads.models import Lead
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='TV Firm')


@pytest.fixture
def advisor(db, tenant):
    return CustomUser.objects.create_user(
        email='adv@tv.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='A', last_name='V',
    )


@pytest.fixture
def admin_user(db, tenant):
    return CustomUser.objects.create_user(
        email='admin@tv.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_TENANT_ADMIN,
        first_name='Ad', last_name='Min',
    )


@pytest.fixture
def lead(db, tenant):
    return Lead.objects.create(
        tenant=tenant, first_name='Bob', last_name='Builder',
        email='bob@b.com', source=Lead.SOURCE_MANUAL,
    )


@pytest.fixture
def campaign(db, tenant, advisor):
    return Campaign.objects.create(
        tenant=tenant, name='TV Campaign', status=Campaign.STATUS_ACTIVE,
        created_by=advisor,
    )


@pytest.fixture
def step(db, campaign):
    return CampaignStep.objects.create(
        campaign=campaign, step_number=1,
        channel=CampaignStep.CHANNEL_EMAIL,
        subject='Hi', content_template='Hello',
        delay_value=1, delay_unit=CampaignStep.DELAY_UNIT_DAYS, delay_days=1,
    )


@pytest.fixture
def enrollment(db, tenant, campaign, lead):
    return CampaignEnrollment.objects.create(
        tenant=tenant, campaign=campaign, lead=lead,
        status=CampaignEnrollment.STATUS_ACTIVE,
    )


@pytest.fixture
def client_auth(advisor):
    c = APIClient()
    c.force_authenticate(user=advisor)
    return c


@pytest.fixture
def admin_client(admin_user):
    c = APIClient()
    c.force_authenticate(user=admin_user)
    return c


@pytest.mark.django_db
class TestLeadTimelineView:

    def test_returns_200(self, client_auth, lead, enrollment, step, tenant):
        from apps.campaign_timeline.services import TimelineService
        TimelineService.generate_for_enrollment(enrollment)
        url = f'/api/v1/timeline/leads/{lead.pk}/'
        resp = client_auth.get(url)
        assert resp.status_code == 200
        assert isinstance(resp.data, list)
        assert len(resp.data) == 1

    def test_404_for_unknown_lead(self, client_auth):
        url = '/api/v1/timeline/leads/999999/'
        resp = client_auth.get(url)
        assert resp.status_code == 404

    def test_unauthenticated_returns_401(self, lead):
        url = f'/api/v1/timeline/leads/{lead.pk}/'
        resp = APIClient().get(url)
        assert resp.status_code == 401


@pytest.mark.django_db
class TestCampaignTimelineView:

    def test_returns_entries_for_campaign(self, client_auth, campaign, enrollment, step):
        from apps.campaign_timeline.services import TimelineService
        TimelineService.generate_for_enrollment(enrollment)
        url = f'/api/v1/timeline/campaigns/{campaign.pk}/'
        resp = client_auth.get(url)
        assert resp.status_code == 200
        assert len(resp.data) == 1


@pytest.mark.django_db
class TestEnrollmentTimelineView:

    def test_returns_entries_for_enrollment(self, client_auth, enrollment, step):
        from apps.campaign_timeline.services import TimelineService
        TimelineService.generate_for_enrollment(enrollment)
        url = f'/api/v1/timeline/enrollments/{enrollment.pk}/'
        resp = client_auth.get(url)
        assert resp.status_code == 200
        assert len(resp.data) == 1


@pytest.mark.django_db
class TestAdvisorTimelineView:

    def test_returns_upcoming_for_advisor(self, client_auth, advisor, lead, enrollment, step):
        from apps.campaign_timeline.services import TimelineService
        TimelineService.generate_for_enrollment(enrollment)
        lead.assigned_advisors.add(advisor)
        url = '/api/v1/timeline/advisor/'
        resp = client_auth.get(url)
        assert resp.status_code == 200

    def test_hours_ahead_param(self, client_auth):
        url = '/api/v1/timeline/advisor/?hours_ahead=12'
        resp = client_auth.get(url)
        assert resp.status_code == 200


@pytest.mark.django_db
class TestTimelineDashboardView:

    def test_admin_can_access(self, admin_client, tenant):
        url = '/api/v1/timeline/dashboard/'
        resp = admin_client.get(url)
        assert resp.status_code == 200
        assert 'pending_now' in resp.data

    def test_advisor_cannot_access_dashboard(self, client_auth):
        url = '/api/v1/timeline/dashboard/'
        resp = client_auth.get(url)
        assert resp.status_code == 403


@pytest.mark.django_db
class TestTenantTimezoneView:

    def test_get_returns_config(self, client_auth, tenant):
        url = '/api/v1/timezones/tenant/'
        resp = client_auth.get(url)
        assert resp.status_code == 200
        assert 'timezone' in resp.data

    def test_advisor_cannot_patch(self, client_auth):
        url = '/api/v1/timezones/tenant/'
        resp = client_auth.patch(url, {'timezone': 'America/Chicago'})
        assert resp.status_code == 403

    def test_admin_can_patch(self, admin_client):
        url = '/api/v1/timezones/tenant/'
        resp = admin_client.patch(url, {'timezone': 'America/Chicago'}, format='json')
        assert resp.status_code == 200
        assert resp.data['timezone'] == 'America/Chicago'


@pytest.mark.django_db
class TestAdvisorTimezoneView:

    def test_put_sets_timezone(self, client_auth, advisor):
        url = '/api/v1/timezones/advisor/'
        resp = client_auth.put(url, {'timezone': 'America/Denver'}, format='json')
        assert resp.status_code == 200
        assert resp.data['timezone'] == 'America/Denver'

    def test_get_returns_timezone(self, client_auth, advisor):
        from apps.timezones.services import TimezoneService
        TimezoneService.set_advisor_timezone(advisor=advisor, timezone_str='America/Phoenix')
        url = '/api/v1/timezones/advisor/'
        resp = client_auth.get(url)
        assert resp.status_code == 200
        assert resp.data['timezone'] == 'America/Phoenix'
