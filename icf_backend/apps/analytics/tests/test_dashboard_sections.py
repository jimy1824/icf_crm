"""
Tests for FM-12 dashboard sections 1–5.
BRU-01: all results must be scoped to tenant — cross-tenant data must never appear.
"""
import datetime
import pytest

from apps.analytics.services import AnalyticsService
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm A')


@pytest.fixture
def other_tenant(db):
    return Tenant.objects.create(firm_name='Test Firm B')


@pytest.fixture
def advisor(db, tenant):
    return CustomUser.objects.create_user(
        email='advisor@testa.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Alex', last_name='Smith',
    )


@pytest.fixture
def other_advisor(db, other_tenant):
    return CustomUser.objects.create_user(
        email='advisor@testb.com', password='pass',
        tenant=other_tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Bob', last_name='Jones',
    )


@pytest.fixture
def lead(db, tenant, advisor):
    from apps.leads.models import Lead
    obj = Lead.objects.create(
        tenant=tenant, first_name='Jane', last_name='Doe',
        email='jane@example.com', status=Lead.STATUS_LEAD,
    )
    obj.assigned_advisors.add(advisor)
    return obj


@pytest.fixture
def other_lead(db, other_tenant, other_advisor):
    from apps.leads.models import Lead
    obj = Lead.objects.create(
        tenant=other_tenant, first_name='Bob', last_name='Other',
        email='bob@example.com', status=Lead.STATUS_LEAD,
    )
    obj.assigned_advisors.add(other_advisor)
    return obj


# ─── Section 1: weekly_lead_analytics ────────────────────────────────────────

@pytest.mark.django_db
class TestWeeklyLeadAnalytics:

    def test_returns_one_entry_per_day(self, tenant):
        data = AnalyticsService.weekly_lead_analytics(tenant=tenant, days=7)
        assert len(data) == 7

    def test_days_15_returns_15_entries(self, tenant):
        data = AnalyticsService.weekly_lead_analytics(tenant=tenant, days=15)
        assert len(data) == 15

    def test_each_entry_has_required_keys(self, tenant):
        data = AnalyticsService.weekly_lead_analytics(tenant=tenant, days=7)
        for entry in data:
            assert 'date' in entry
            assert 'received' in entry
            assert 'responded' in entry

    def test_counts_lead_created_today(self, tenant, lead):
        # lead fixture is created today
        data = AnalyticsService.weekly_lead_analytics(tenant=tenant, days=7)
        total_received = sum(e['received'] for e in data)
        assert total_received >= 1

    def test_bru01_other_tenant_lead_not_counted(self, tenant, other_lead):
        data = AnalyticsService.weekly_lead_analytics(tenant=tenant, days=7)
        total_received = sum(e['received'] for e in data)
        assert total_received == 0

    def test_advisor_filter_scopes_to_advisor_leads(self, tenant, advisor, lead, db):
        from apps.leads.models import Lead
        other_advisor2 = CustomUser.objects.create_user(
            email='other2@testa.com', password='pass',
            tenant=tenant, role=CustomUser.ROLE_ADVISOR,
            first_name='X', last_name='Y',
        )
        # Create a lead assigned to other_advisor2 — should not appear in advisor filter
        other_lead2 = Lead.objects.create(
            tenant=tenant, first_name='Not', last_name='Mine',
            email='notmine@example.com', status=Lead.STATUS_LEAD,
        )
        other_lead2.assigned_advisors.add(other_advisor2)

        data = AnalyticsService.weekly_lead_analytics(tenant=tenant, days=7, advisor=advisor)
        total = sum(e['received'] for e in data)
        # Only lead (assigned to advisor) should count
        assert total == 1


# ─── Section 2: today_leads ───────────────────────────────────────────────────

@pytest.mark.django_db
class TestTodayLeads:

    def test_returns_list(self, tenant, lead):
        result = AnalyticsService.today_leads(tenant=tenant)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_entry_keys(self, tenant, lead):
        result = AnalyticsService.today_leads(tenant=tenant)
        entry = result[0]
        for key in ('id', 'name', 'territory', 'advisor', 'campaign', 'status', 'created_at'):
            assert key in entry

    def test_bru01_other_tenant_excluded(self, tenant, other_lead):
        result = AnalyticsService.today_leads(tenant=tenant)
        assert len(result) == 0

    def test_advisor_filter(self, tenant, advisor, lead, db):
        from apps.leads.models import Lead
        other_advisor2 = CustomUser.objects.create_user(
            email='oa2@testa.com', password='pass',
            tenant=tenant, role=CustomUser.ROLE_ADVISOR,
            first_name='Z', last_name='Z',
        )
        other_lead2 = Lead.objects.create(
            tenant=tenant, first_name='Other', last_name='Lead',
            email='otherlead@example.com', status=Lead.STATUS_LEAD,
        )
        other_lead2.assigned_advisors.add(other_advisor2)

        result = AnalyticsService.today_leads(tenant=tenant, advisor=advisor)
        ids = [r['id'] for r in result]
        assert lead.id in ids
        assert other_lead2.id not in ids


# ─── Section 3: today_activities ─────────────────────────────────────────────

@pytest.mark.django_db
class TestTodayActivities:

    def test_returns_list(self, tenant):
        result = AnalyticsService.today_activities(tenant=tenant)
        assert isinstance(result, list)

    def test_bru01_other_tenant_excluded(self, tenant, other_tenant, other_lead, db):
        from apps.campaigns.models import Campaign, CampaignEnrollment, CampaignStep
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        from django.utils import timezone

        campaign = Campaign.objects.create(
            tenant=other_tenant, name='B Campaign', status='active',
        )
        step = CampaignStep.objects.create(
            campaign=campaign, step_number=1, channel='email',
            content_template='hi', delay_value=0, delay_unit='hours', delay_days=0,
        )
        enrollment = CampaignEnrollment.objects.create(
            tenant=other_tenant, campaign=campaign,
            lead=other_lead, status='active', current_step=0,
        )
        CampaignExecutionTimeline.objects.create(
            tenant=other_tenant,
            enrollment=enrollment,
            campaign=campaign,
            lead=other_lead,
            campaign_step=step,
            step_order=1, step_type='email',
            subject_snapshot='', body_snapshot='',
            scheduled_at=timezone.now(),
            status='pending',
        )

        result = AnalyticsService.today_activities(tenant=tenant)
        assert len(result) == 0


# ─── Section 4: today_responses ──────────────────────────────────────────────

@pytest.mark.django_db
class TestTodayResponses:

    def test_returns_list(self, tenant):
        result = AnalyticsService.today_responses(tenant=tenant)
        assert isinstance(result, list)

    def test_inbound_reply_appears(self, tenant, lead, advisor, db):
        from apps.communications.models import Communication
        comm = Communication.objects.create(
            tenant=tenant, lead=lead, sent_by=advisor,
            channel='email', direction='inbound', status='received',
            subject='Interested!', is_reply=True,
            external_id='test-reply-001',
        )
        result = AnalyticsService.today_responses(tenant=tenant)
        ids = [r['id'] for r in result]
        assert comm.id in ids

    def test_non_reply_excluded(self, tenant, lead, advisor, db):
        from apps.communications.models import Communication
        Communication.objects.create(
            tenant=tenant, lead=lead, sent_by=advisor,
            channel='email', direction='outbound', status='delivered',
            subject='Hi there', is_reply=False,
            external_id='test-nonreply-001',
        )
        result = AnalyticsService.today_responses(tenant=tenant)
        assert len(result) == 0

    def test_bru01_other_tenant_reply_excluded(self, tenant, other_tenant, other_lead, other_advisor, db):
        from apps.communications.models import Communication
        Communication.objects.create(
            tenant=other_tenant, lead=other_lead, sent_by=other_advisor,
            channel='email', direction='inbound', status='received',
            subject='Other reply', is_reply=True,
            external_id='test-other-reply-001',
        )
        result = AnalyticsService.today_responses(tenant=tenant)
        assert len(result) == 0

    def test_entry_has_required_keys(self, tenant, lead, advisor, db):
        from apps.communications.models import Communication
        Communication.objects.create(
            tenant=tenant, lead=lead, sent_by=advisor,
            channel='sms', direction='inbound', status='received',
            subject='Yes call me', is_reply=True,
            external_id='test-keys-001',
        )
        result = AnalyticsService.today_responses(tenant=tenant)
        assert len(result) >= 1
        for key in ('id', 'lead_name', 'advisor', 'response_type', 'message_preview', 'received_at'):
            assert key in result[0]


# ─── Section 5: territory_lead_distribution ──────────────────────────────────

@pytest.mark.django_db
class TestTerritoryLeadDistribution:

    def test_returns_list(self, tenant):
        result = AnalyticsService.territory_lead_distribution(tenant=tenant, days=7)
        assert isinstance(result, list)

    def test_entry_has_required_keys(self, tenant, lead, db):
        from apps.territories.models import Territory
        from apps.leads.models import Lead
        territory = Territory.objects.create(tenant=tenant, name='North Zone')
        lead_w_territory = Lead.objects.create(
            tenant=tenant, first_name='T', last_name='Lead',
            email='t@example.com', status=Lead.STATUS_LEAD, territory=territory,
        )
        result = AnalyticsService.territory_lead_distribution(tenant=tenant, days=7)
        assert len(result) >= 1
        for key in ('territory', 'territory_id', 'lead_count'):
            assert key in result[0]

    def test_bru01_other_tenant_territory_excluded(self, tenant, other_tenant, other_lead, db):
        from apps.territories.models import Territory
        from apps.leads.models import Lead
        other_territory = Territory.objects.create(tenant=other_tenant, name='Other Zone')
        other_lead.territory = other_territory
        other_lead.save(update_fields=['territory'])

        result = AnalyticsService.territory_lead_distribution(tenant=tenant, days=7)
        territory_names = [r['territory'] for r in result]
        assert 'Other Zone' not in territory_names

    def test_ordered_by_count_descending(self, tenant, db):
        from apps.territories.models import Territory
        from apps.leads.models import Lead
        t1 = Territory.objects.create(tenant=tenant, name='Big Zone')
        t2 = Territory.objects.create(tenant=tenant, name='Small Zone')
        for i in range(3):
            Lead.objects.create(
                tenant=tenant, first_name=f'A{i}', last_name='B',
                email=f'a{i}big@example.com', status=Lead.STATUS_LEAD, territory=t1,
            )
        Lead.objects.create(
            tenant=tenant, first_name='C', last_name='D',
            email='csmall@example.com', status=Lead.STATUS_LEAD, territory=t2,
        )
        result = AnalyticsService.territory_lead_distribution(tenant=tenant, days=7)
        assert result[0]['territory'] == 'Big Zone'
        assert result[0]['lead_count'] == 3


# ─── New advisor_dashboard fields ─────────────────────────────────────────────

@pytest.mark.django_db
class TestAdvisorDashboardExtended:

    def test_has_pipeline_stages(self, tenant, advisor):
        data = AnalyticsService.advisor_dashboard(tenant=tenant, advisor=advisor)
        assert 'pipeline_stages' in data
        assert isinstance(data['pipeline_stages'], list)

    def test_has_conversion_rate(self, tenant, advisor):
        data = AnalyticsService.advisor_dashboard(tenant=tenant, advisor=advisor)
        assert 'conversion_rate' in data

    def test_has_active_campaigns(self, tenant, advisor):
        data = AnalyticsService.advisor_dashboard(tenant=tenant, advisor=advisor)
        assert 'active_campaigns' in data

    def test_pipeline_stages_include_stage_and_count(self, tenant, advisor, lead):
        data = AnalyticsService.advisor_dashboard(tenant=tenant, advisor=advisor)
        stages = data['pipeline_stages']
        assert len(stages) >= 1
        assert 'stage' in stages[0]
        assert 'count' in stages[0]

    def test_bru01_pipeline_only_own_leads(self, tenant, other_tenant, advisor, db):
        from apps.leads.models import Lead
        other_advisor2 = CustomUser.objects.create_user(
            email='oa3@testa.com', password='pass',
            tenant=tenant, role=CustomUser.ROLE_ADVISOR,
            first_name='X', last_name='X',
        )
        cross_lead = Lead.objects.create(
            tenant=tenant, first_name='Cross', last_name='Lead',
            email='cross@example.com', status=Lead.STATUS_LEAD,
        )
        cross_lead.assigned_advisors.add(other_advisor2)

        data = AnalyticsService.advisor_dashboard(tenant=tenant, advisor=advisor)
        total_in_stages = sum(s['count'] for s in data['pipeline_stages'])
        assert total_in_stages == 0  # advisor has no leads assigned
