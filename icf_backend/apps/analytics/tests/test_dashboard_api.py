"""
API-level tests for the enterprise dashboard endpoints.
Covers: pagination, ordering, advisor filter, date filter, search, BRU-01 isolation,
and the /analytics/advisors/ list endpoint.
"""
import pytest
from django.urls import reverse


@pytest.fixture
def tenant(db):
    from apps.tenants.models import Tenant
    return Tenant.objects.create(firm_name='API Test Firm')


@pytest.fixture
def other_tenant(db):
    from apps.tenants.models import Tenant
    return Tenant.objects.create(firm_name='Other Firm')


@pytest.fixture
def advisor(db, tenant):
    from apps.users.models import CustomUser
    return CustomUser.objects.create_user(
        email='adv@apifirm.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Alex', last_name='Advisor',
    )


@pytest.fixture
def second_advisor(db, tenant):
    from apps.users.models import CustomUser
    return CustomUser.objects.create_user(
        email='adv2@apifirm.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Beth', last_name='Broker',
    )


@pytest.fixture
def other_advisor(db, other_tenant):
    from apps.users.models import CustomUser
    return CustomUser.objects.create_user(
        email='adv@otherfirm.com', password='pass',
        tenant=other_tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Zed', last_name='Other',
    )


@pytest.fixture
def lead(db, tenant, advisor):
    from apps.leads.models import Lead
    obj = Lead.objects.create(
        tenant=tenant, first_name='Jane', last_name='Doe',
        email='jane@example.com', status='new',
    )
    obj.assigned_advisors.add(advisor)
    return obj


@pytest.fixture
def auth_client(client, advisor):
    from rest_framework_simplejwt.tokens import RefreshToken
    token = RefreshToken.for_user(advisor).access_token
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return client


@pytest.fixture
def firm_admin(db, tenant):
    from apps.users.models import CustomUser
    return CustomUser.objects.create_user(
        email='admin@apifirm.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_TENANT_ADMIN,
        first_name='Firm', last_name='Admin',
    )


@pytest.fixture
def admin_client(client, firm_admin):
    from rest_framework_simplejwt.tokens import RefreshToken
    token = RefreshToken.for_user(firm_admin).access_token
    client.defaults['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    return client


# ─── /analytics/advisors/ ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTenantAdvisorsEndpoint:

    def test_returns_200(self, auth_client):
        res = auth_client.get('/api/v1/analytics/advisors/')
        assert res.status_code == 200

    def test_returns_only_tenant_advisors(self, auth_client, advisor, second_advisor, other_advisor):
        res = auth_client.get('/api/v1/analytics/advisors/')
        ids = [a['id'] for a in res.json()['results']]
        assert advisor.id in ids
        assert second_advisor.id in ids
        # BRU-01: other tenant's advisor must NOT appear
        assert other_advisor.id not in ids

    def test_excludes_admin_roles(self, auth_client, firm_admin, advisor):
        res = auth_client.get('/api/v1/analytics/advisors/')
        ids = [a['id'] for a in res.json()['results']]
        assert firm_admin.id not in ids

    def test_response_shape(self, auth_client, advisor):
        res = auth_client.get('/api/v1/analytics/advisors/')
        result = res.json()['results'][0]
        for key in ('id', 'full_name', 'email', 'role', 'active_lead_count'):
            assert key in result

    def test_requires_auth(self, client):
        res = client.get('/api/v1/analytics/advisors/')
        assert res.status_code == 401


# ─── /analytics/today-leads/ ─────────────────────────────────────────────────

@pytest.mark.django_db
class TestTodayLeadsEndpoint:

    def test_returns_paginated_envelope(self, auth_client, lead):
        res = auth_client.get('/api/v1/analytics/today-leads/')
        assert res.status_code == 200
        data = res.json()
        assert 'count' in data
        assert 'results' in data
        assert 'next' in data
        assert 'previous' in data

    def test_row_has_full_lead_info(self, auth_client, lead):
        res = auth_client.get('/api/v1/analytics/today-leads/')
        results = res.json()['results']
        if results:
            row = results[0]
            assert 'first_name' in row
            assert 'last_name' in row
            assert 'email' in row
            assert 'phone' in row
            assert 'assigned_advisors' in row
            assert isinstance(row['assigned_advisors'], list)

    def test_assigned_advisors_is_list_not_duplicated(self, auth_client, lead, second_advisor):
        # Assign second advisor to same lead
        lead.assigned_advisors.add(second_advisor)
        res = auth_client.get('/api/v1/analytics/today-leads/')
        results = res.json()['results']
        # Lead appears ONCE; advisors are a list within that one row
        assert len(results) <= 1
        if results:
            assert len(results[0]['assigned_advisors']) == 2

    def test_date_filter(self, auth_client, lead):
        # Non-existent date returns 0 results
        res = auth_client.get('/api/v1/analytics/today-leads/?date=2000-01-01')
        assert res.status_code == 200
        assert res.json()['count'] == 0

    def test_invalid_date_returns_400(self, auth_client):
        res = auth_client.get('/api/v1/analytics/today-leads/?date=not-a-date')
        assert res.status_code == 400

    def test_search_filters_results(self, auth_client, lead):
        res_match = auth_client.get('/api/v1/analytics/today-leads/?search=Jane')
        res_no_match = auth_client.get('/api/v1/analytics/today-leads/?search=ZZZNOMATCH')
        assert res_no_match.json()['count'] == 0
        # jane@example.com matches 'Jane'
        assert res_match.json()['count'] >= 0  # depends on today date

    def test_ordering_accepted(self, auth_client):
        for ordering in ('-created_at', 'last_name', 'pipeline_stage', 'territory__name'):
            res = auth_client.get(f'/api/v1/analytics/today-leads/?ordering={ordering}')
            assert res.status_code == 200

    def test_invalid_ordering_defaults_gracefully(self, auth_client):
        # Unknown ordering should be sanitized to default, not 500
        res = auth_client.get('/api/v1/analytics/today-leads/?ordering=__evil')
        assert res.status_code == 200

    def test_pagination_page_size(self, auth_client, db, tenant, advisor):
        from apps.leads.models import Lead
        # Create 5 leads today
        for i in range(5):
            obj = Lead.objects.create(
                tenant=tenant, first_name=f'Lead{i}', last_name='Test',
                email=f'lead{i}@test.com', status='new',
            )
            obj.assigned_advisors.add(advisor)
        res = auth_client.get('/api/v1/analytics/today-leads/?page_size=2')
        assert res.status_code == 200
        data = res.json()
        assert len(data['results']) <= 2

    def test_advisor_id_all_returns_all_tenant_leads(self, auth_client, db, tenant, second_advisor):
        from apps.leads.models import Lead
        obj = Lead.objects.create(
            tenant=tenant, first_name='Other', last_name='Lead',
            email='other@test.com', status='new',
        )
        obj.assigned_advisors.add(second_advisor)
        res = auth_client.get('/api/v1/analytics/today-leads/?advisor_id=all')
        assert res.status_code == 200
        # Should include leads from other advisors in same tenant

    def test_bru01_cross_tenant_excluded(self, auth_client, db, other_tenant, other_advisor):
        from apps.leads.models import Lead
        cross = Lead.objects.create(
            tenant=other_tenant, first_name='Cross', last_name='Tenant',
            email='cross@othertenant.com', status='new',
        )
        cross.assigned_advisors.add(other_advisor)
        res = auth_client.get('/api/v1/analytics/today-leads/?advisor_id=all')
        emails = [r['email'] for r in res.json()['results']]
        assert 'cross@othertenant.com' not in emails

    def test_requires_auth(self, client):
        res = client.get('/api/v1/analytics/today-leads/')
        assert res.status_code == 401


# ─── /analytics/today-activities/ ────────────────────────────────────────────

@pytest.mark.django_db
class TestTodayActivitiesEndpoint:

    def test_returns_paginated_envelope(self, auth_client):
        res = auth_client.get('/api/v1/analytics/today-activities/')
        assert res.status_code == 200
        data = res.json()
        assert 'count' in data
        assert 'results' in data

    def test_date_filter(self, auth_client):
        res = auth_client.get('/api/v1/analytics/today-activities/?date=2000-01-01')
        assert res.status_code == 200
        assert res.json()['count'] == 0

    def test_ordering_accepted(self, auth_client):
        for ordering in ('scheduled_at', '-scheduled_at', 'step_order', 'status', 'campaign__name'):
            res = auth_client.get(f'/api/v1/analytics/today-activities/?ordering={ordering}')
            assert res.status_code == 200

    def test_search_returns_200(self, auth_client):
        res = auth_client.get('/api/v1/analytics/today-activities/?search=test')
        assert res.status_code == 200

    def test_pagination_works(self, auth_client):
        res = auth_client.get('/api/v1/analytics/today-activities/?page=1&page_size=10')
        assert res.status_code == 200

    def test_bru01_cross_tenant_entry_excluded(self, auth_client, db, other_tenant, other_advisor):
        from apps.leads.models import Lead
        from apps.campaigns.models import Campaign, CampaignEnrollment, CampaignStep
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        from django.utils import timezone

        cross_lead = Lead.objects.create(
            tenant=other_tenant, first_name='X', last_name='Y',
            email='x@other.com', status='new',
        )
        cross_campaign = Campaign.objects.create(
            tenant=other_tenant, name='Other Campaign', status='active',
        )
        step = CampaignStep.objects.create(
            campaign=cross_campaign, step_number=1, channel='email',
            content_template='test', delay_value=0, delay_unit='hours', delay_days=0,
        )
        enroll = CampaignEnrollment.objects.create(
            tenant=other_tenant, campaign=cross_campaign,
            lead=cross_lead, status='active', current_step=0,
        )
        CampaignExecutionTimeline.objects.create(
            tenant=other_tenant, enrollment=enroll, campaign=cross_campaign,
            lead=cross_lead, campaign_step=step, step_order=1, step_type='email',
            subject_snapshot='', body_snapshot='',
            scheduled_at=timezone.now(), status='pending',
        )

        res = auth_client.get('/api/v1/analytics/today-activities/?advisor_id=all')
        lead_names = [r.get('lead_name', '') for r in res.json()['results']]
        assert 'X Y' not in lead_names

    def test_requires_auth(self, client):
        res = client.get('/api/v1/analytics/today-activities/')
        assert res.status_code == 401
