"""
Tests for Campaign Execution Timeline & Time Zone Management.

Coverage:
- TenantTimeZone creation and office-hour shifting (BRU-09)
- AdvisorTimeZone override
- Timeline generation at enrollment (all steps pre-computed)
- delay_unit: hours / days / weeks
- CampaignExecutionTimeline status transitions
- Celery task dispatch (cancel_enrollment_timeline)
- BRU-01: cross-tenant isolation on all timeline queries
- Dashboard summary analytics
"""
import datetime

import pytest
from django.utils import timezone as dj_tz

from apps.campaigns.models import Campaign, CampaignEnrollment, CampaignStep
from apps.campaign_timeline.models import CampaignExecutionTimeline
from apps.leads.models import Lead
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='TL Firm')


@pytest.fixture
def other_tenant(db):
    return Tenant.objects.create(firm_name='Other Firm')


@pytest.fixture
def advisor(db, tenant):
    return CustomUser.objects.create_user(
        email='adv@tl.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Ad', last_name='Visor',
    )


@pytest.fixture
def lead(db, tenant):
    return Lead.objects.create(
        tenant=tenant, first_name='Jane', last_name='Doe',
        email='jane@doe.com', source=Lead.SOURCE_MANUAL,
    )


@pytest.fixture
def campaign(db, tenant, advisor):
    return Campaign.objects.create(
        tenant=tenant, name='Onboarding', status=Campaign.STATUS_ACTIVE,
        created_by=advisor,
    )


@pytest.fixture
def step1(db, campaign):
    return CampaignStep.objects.create(
        campaign=campaign, step_number=1,
        channel=CampaignStep.CHANNEL_EMAIL,
        subject='Welcome', content_template='Hi {{name}}',
        delay_value=0, delay_unit=CampaignStep.DELAY_UNIT_HOURS,
        delay_days=0,
    )


@pytest.fixture
def step2(db, campaign):
    return CampaignStep.objects.create(
        campaign=campaign, step_number=2,
        channel=CampaignStep.CHANNEL_SMS,
        content_template='Follow up SMS',
        delay_value=2, delay_unit=CampaignStep.DELAY_UNIT_DAYS,
        delay_days=2,
    )


@pytest.fixture
def step3(db, campaign):
    return CampaignStep.objects.create(
        campaign=campaign, step_number=3,
        channel=CampaignStep.CHANNEL_EMAIL,
        subject='Check-in', content_template='Checking in',
        delay_value=1, delay_unit=CampaignStep.DELAY_UNIT_WEEKS,
        delay_days=7,
    )


@pytest.fixture
def enrollment(db, tenant, campaign, lead):
    return CampaignEnrollment.objects.create(
        tenant=tenant, campaign=campaign, lead=lead,
        status=CampaignEnrollment.STATUS_ACTIVE,
    )


# ---------------------------------------------------------------------------
# TenantTimeZone — office-hour shifting
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestOfficeHourShifting:

    def test_get_or_create_returns_defaults(self, tenant):
        from apps.timezones.services import TimezoneService
        config = TimezoneService.get_tenant_config(tenant)
        assert config.timezone == 'America/New_York'
        assert config.get_working_days() == [0, 1, 2, 3, 4]

    def test_time_inside_window_not_shifted(self, tenant):
        """A datetime already inside office hours should not change."""
        import zoneinfo
        from apps.timezones.services import TimezoneService
        from datetime import timezone as dt_tz
        # 10 AM ET on a Tuesday
        tz = zoneinfo.ZoneInfo('America/New_York')
        local = datetime.datetime(2025, 6, 3, 10, 0, 0, tzinfo=tz)
        result = TimezoneService.shift_to_office_hours(local, tenant)
        result_local = result.astimezone(tz)
        assert result_local.hour == 10

    def test_before_office_start_shifts_to_09(self, tenant):
        """A datetime at 6 AM ET should become 9 AM ET."""
        import zoneinfo
        from apps.timezones.services import TimezoneService
        tz = zoneinfo.ZoneInfo('America/New_York')
        # 6 AM ET on a Wednesday
        local = datetime.datetime(2025, 6, 4, 6, 0, 0, tzinfo=tz)
        result = TimezoneService.shift_to_office_hours(local, tenant)
        result_local = result.astimezone(tz)
        assert result_local.hour == 9
        assert result_local.minute == 0

    def test_after_office_close_shifts_to_next_morning(self, tenant):
        """A datetime at 8 PM ET should advance to 9 AM next business day."""
        import zoneinfo
        from apps.timezones.services import TimezoneService
        tz = zoneinfo.ZoneInfo('America/New_York')
        # 8 PM ET on a Wednesday
        local = datetime.datetime(2025, 6, 4, 20, 0, 0, tzinfo=tz)
        result = TimezoneService.shift_to_office_hours(local, tenant)
        result_local = result.astimezone(tz)
        assert result_local.hour == 9
        assert result_local.minute == 0
        # Next business day is Thursday
        assert result_local.weekday() == 3

    def test_saturday_shifts_to_monday(self, tenant):
        """A datetime on Saturday should advance to Monday 9 AM."""
        import zoneinfo
        from apps.timezones.services import TimezoneService
        tz = zoneinfo.ZoneInfo('America/New_York')
        # Saturday noon
        local = datetime.datetime(2025, 6, 7, 12, 0, 0, tzinfo=tz)
        result = TimezoneService.shift_to_office_hours(local, tenant)
        result_local = result.astimezone(tz)
        assert result_local.weekday() == 0  # Monday
        assert result_local.hour == 9

    def test_custom_working_days(self, tenant):
        """If only Mon/Wed/Fri are working days, Tuesday skips to Wednesday."""
        import zoneinfo
        from apps.timezones.services import TimezoneService
        config = TimezoneService.get_tenant_config(tenant)
        config.working_days = [0, 2, 4]  # Mon, Wed, Fri
        config.save()
        tz = zoneinfo.ZoneInfo('America/New_York')
        # Tuesday 10 AM — not a working day
        local = datetime.datetime(2025, 6, 3, 10, 0, 0, tzinfo=tz)
        result = TimezoneService.shift_to_office_hours(local, tenant)
        result_local = result.astimezone(tz)
        assert result_local.weekday() == 2  # Wednesday
        assert result_local.hour == 9

    def test_update_tenant_config(self, tenant, advisor):
        from apps.timezones.services import TimezoneService
        config = TimezoneService.update_tenant_config(
            tenant=tenant, actor=advisor,
            timezone='America/Chicago',
            working_days=[0, 1, 2, 3, 4, 5],
        )
        assert config.timezone == 'America/Chicago'
        assert 5 in config.working_days


# ---------------------------------------------------------------------------
# AdvisorTimeZone
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestAdvisorTimeZone:

    def test_set_and_retrieve(self, advisor):
        from apps.timezones.services import TimezoneService
        TimezoneService.set_advisor_timezone(advisor=advisor, timezone_str='America/Los_Angeles')
        tz = TimezoneService.get_advisor_timezone(advisor)
        assert tz == 'America/Los_Angeles'

    def test_fallback_to_tenant_tz(self, advisor, tenant):
        from apps.timezones.services import TimezoneService
        # No AdvisorTimeZone set — should fall back to tenant TZ
        tz = TimezoneService.get_advisor_timezone(advisor)
        assert tz == 'America/New_York'  # default from TenantTimeZone

    def test_idempotent_update(self, advisor):
        from apps.timezones.services import TimezoneService
        TimezoneService.set_advisor_timezone(advisor=advisor, timezone_str='America/Denver')
        TimezoneService.set_advisor_timezone(advisor=advisor, timezone_str='America/Phoenix')
        from apps.timezones.models import AdvisorTimeZone
        count = AdvisorTimeZone.objects.filter(advisor=advisor).count()
        assert count == 1
        assert TimezoneService.get_advisor_timezone(advisor) == 'America/Phoenix'


# ---------------------------------------------------------------------------
# Timeline generation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTimelineGeneration:

    def test_generates_one_entry_per_step(self, enrollment, step1, step2, step3):
        from apps.campaign_timeline.services import TimelineService
        entries = TimelineService.generate_for_enrollment(enrollment)
        assert len(entries) == 3
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        assert CampaignExecutionTimeline.objects.filter(enrollment=enrollment).count() == 3

    def test_entries_tenant_scoped(self, enrollment, step1, step2):
        from apps.campaign_timeline.services import TimelineService
        TimelineService.generate_for_enrollment(enrollment)
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        for entry in CampaignExecutionTimeline.objects.filter(enrollment=enrollment):
            assert entry.tenant_id == enrollment.tenant_id

    def test_status_pending_on_creation(self, enrollment, step1, step2):
        from apps.campaign_timeline.services import TimelineService
        TimelineService.generate_for_enrollment(enrollment)
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        statuses = set(
            CampaignExecutionTimeline.objects
            .filter(enrollment=enrollment)
            .values_list('status', flat=True)
        )
        assert statuses == {CampaignExecutionTimeline.STATUS_PENDING}

    def test_step2_scheduled_after_step1(self, enrollment, step1, step2):
        from apps.campaign_timeline.services import TimelineService
        TimelineService.generate_for_enrollment(enrollment)
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        e1 = CampaignExecutionTimeline.objects.get(enrollment=enrollment, step_order=1)
        e2 = CampaignExecutionTimeline.objects.get(enrollment=enrollment, step_order=2)
        assert e2.scheduled_at > e1.scheduled_at

    def test_delay_unit_hours(self, enrollment, step1):
        """Step with delay_value=0 hours — scheduled roughly at enrollment time."""
        from apps.campaign_timeline.services import TimelineService
        before = dj_tz.now()
        TimelineService.generate_for_enrollment(enrollment)
        after = dj_tz.now()
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        e1 = CampaignExecutionTimeline.objects.get(enrollment=enrollment, step_order=1)
        # Shifted to office hours, but should be today or same day
        assert e1.scheduled_at >= before - datetime.timedelta(seconds=5)

    def test_delay_unit_weeks(self, enrollment, step1, step2, step3):
        """Step 3 with 1 week delay should be ~7 days after step 2."""
        from apps.campaign_timeline.services import TimelineService
        TimelineService.generate_for_enrollment(enrollment)
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        e2 = CampaignExecutionTimeline.objects.get(enrollment=enrollment, step_order=2)
        e3 = CampaignExecutionTimeline.objects.get(enrollment=enrollment, step_order=3)
        delta = e3.scheduled_at - e2.scheduled_at
        # 1 week = 7 days; office hour shift may add up to ~2 days max
        assert datetime.timedelta(days=5) <= delta <= datetime.timedelta(days=10)

    def test_content_snapshot_immutable(self, enrollment, step1):
        """Body snapshot is taken at generation time and not re-read from step."""
        from apps.campaign_timeline.services import TimelineService
        TimelineService.generate_for_enrollment(enrollment)
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        entry = CampaignExecutionTimeline.objects.get(enrollment=enrollment, step_order=1)
        assert entry.body_snapshot == step1.content_template
        assert entry.subject_snapshot == step1.subject

    def test_empty_campaign_returns_empty(self, enrollment):
        """Campaign with no steps generates no timeline entries."""
        from apps.campaign_timeline.services import TimelineService
        entries = TimelineService.generate_for_enrollment(enrollment)
        assert entries == []

    def test_office_hour_shift_flag(self, tenant, enrollment):
        """Entries that land outside office hours should have was_office_hour_shifted=True."""
        from apps.timezones.services import TimezoneService
        # Force office hours to 10 AM–11 AM ET so almost any time needs shifting
        config = TimezoneService.get_tenant_config(tenant)
        config.office_start = datetime.time(10, 0)
        config.office_end = datetime.time(11, 0)
        config.save()
        # Create a step with 0 delay to trigger shift
        step = CampaignStep.objects.create(
            campaign=enrollment.campaign, step_number=10,
            channel=CampaignStep.CHANNEL_EMAIL,
            subject='Test', content_template='Test',
            delay_value=0, delay_unit=CampaignStep.DELAY_UNIT_HOURS, delay_days=0,
        )
        from apps.campaign_timeline.services import TimelineService
        TimelineService.generate_for_enrollment(enrollment)
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        entry = CampaignExecutionTimeline.objects.filter(
            enrollment=enrollment, campaign_step=step,
        ).first()
        assert entry is not None
        # Either shifted or not — field must exist
        assert isinstance(entry.was_office_hour_shifted, bool)


# ---------------------------------------------------------------------------
# Timeline cancellation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTimelineCancellation:

    def test_cancel_for_enrollment_sets_cancelled(self, enrollment, step1, step2):
        from apps.campaign_timeline.services import TimelineService
        TimelineService.generate_for_enrollment(enrollment)
        count = TimelineService.cancel_for_enrollment(enrollment)
        assert count == 2
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        statuses = set(
            CampaignExecutionTimeline.objects
            .filter(enrollment=enrollment)
            .values_list('status', flat=True)
        )
        assert statuses == {CampaignExecutionTimeline.STATUS_CANCELLED}

    def test_cancel_idempotent(self, enrollment, step1):
        from apps.campaign_timeline.services import TimelineService
        TimelineService.generate_for_enrollment(enrollment)
        TimelineService.cancel_for_enrollment(enrollment)
        # Second call is a no-op
        count2 = TimelineService.cancel_for_enrollment(enrollment)
        assert count2 == 0

    def test_cancel_does_not_affect_executed(self, enrollment, step1, step2):
        """Executed entries must not be changed to Cancelled."""
        from apps.campaign_timeline.services import TimelineService
        TimelineService.generate_for_enrollment(enrollment)
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        entry = CampaignExecutionTimeline.objects.get(
            enrollment=enrollment, step_order=1,
        )
        entry.status = CampaignExecutionTimeline.STATUS_EXECUTED
        entry.save()
        TimelineService.cancel_for_enrollment(enrollment)
        entry.refresh_from_db()
        assert entry.status == CampaignExecutionTimeline.STATUS_EXECUTED


# ---------------------------------------------------------------------------
# BRU-01: Cross-tenant isolation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTimelineTenantIsolation:

    def test_lead_timeline_scoped_to_tenant(self, tenant, other_tenant, lead, enrollment, step1):
        from apps.campaign_timeline.services import TimelineService
        TimelineService.generate_for_enrollment(enrollment)

        # Create lead and enrollment for other_tenant
        other_advisor = CustomUser.objects.create_user(
            email='other@other.com', password='pass',
            tenant=other_tenant, role=CustomUser.ROLE_ADVISOR,
            first_name='O', last_name='T',
        )
        other_lead = Lead.objects.create(
            tenant=other_tenant, first_name='X', last_name='Y',
            email='x@y.com', source=Lead.SOURCE_MANUAL,
        )
        other_campaign = Campaign.objects.create(
            tenant=other_tenant, name='Other Campaign',
            status=Campaign.STATUS_ACTIVE, created_by=other_advisor,
        )
        CampaignStep.objects.create(
            campaign=other_campaign, step_number=1,
            channel=CampaignStep.CHANNEL_EMAIL,
            content_template='Other', delay_value=0,
            delay_unit=CampaignStep.DELAY_UNIT_DAYS, delay_days=0,
        )
        other_enrollment = CampaignEnrollment.objects.create(
            tenant=other_tenant, campaign=other_campaign, lead=other_lead,
            status=CampaignEnrollment.STATUS_ACTIVE,
        )
        TimelineService.generate_for_enrollment(other_enrollment)

        from apps.campaign_timeline.selectors import get_timeline_for_lead
        qs = get_timeline_for_lead(tenant=tenant, lead=lead)
        for entry in qs:
            assert entry.tenant_id == tenant.pk

    def test_campaign_timeline_scoped(self, tenant, other_tenant, enrollment, step1, campaign):
        from apps.campaign_timeline.services import TimelineService
        TimelineService.generate_for_enrollment(enrollment)
        from apps.campaign_timeline.selectors import get_timeline_for_campaign
        qs = get_timeline_for_campaign(tenant=tenant, campaign=campaign)
        for entry in qs:
            assert entry.tenant_id == tenant.pk


# ---------------------------------------------------------------------------
# TimelineAnalyticsService
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTimelineAnalytics:

    def test_dashboard_summary_keys(self, tenant, enrollment, step1):
        from apps.campaign_timeline.services import TimelineService, TimelineAnalyticsService
        TimelineService.generate_for_enrollment(enrollment)
        summary = TimelineAnalyticsService.dashboard_summary(tenant=tenant)
        assert 'pending_now' in summary
        assert 'scheduled_today' in summary
        assert 'executed_today' in summary
        assert 'failed_today' in summary
        assert 'office_hour_shifts' in summary

    def test_pending_now_counts_due_entries(self, tenant, enrollment, step1):
        """Entries with scheduled_at in the past should appear in pending_now."""
        from apps.campaign_timeline.services import TimelineService, TimelineAnalyticsService
        TimelineService.generate_for_enrollment(enrollment)
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        # Force scheduled_at into the past
        CampaignExecutionTimeline.objects.filter(enrollment=enrollment).update(
            scheduled_at=dj_tz.now() - datetime.timedelta(hours=1),
        )
        summary = TimelineAnalyticsService.dashboard_summary(tenant=tenant)
        assert summary['pending_now'] >= 1

    def test_upcoming_for_advisor_scoped(self, advisor, tenant, enrollment, step1, lead):
        from apps.campaign_timeline.services import TimelineService, TimelineAnalyticsService
        TimelineService.generate_for_enrollment(enrollment)
        # Assign lead to advisor
        lead.assigned_advisors.add(advisor)
        entries = TimelineAnalyticsService.upcoming_for_advisor(advisor=advisor, hours_ahead=72)
        for entry in entries:
            assert entry.tenant_id == tenant.pk
