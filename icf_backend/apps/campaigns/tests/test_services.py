"""
Campaign service tests — covers all Phase 3 BRUs for campaigns:
BRU-03: no duplicate active enrollment
BRU-07: opt-out prevents enroll
BRU-09: campaign must have steps to activate
BRU-17: reply stops campaign (via stop_all_enrollments_for_subject)
BRU-19: suppressed lead prevents enroll
BRU-21: manual stop of enrollment
BRU-01: tenant isolation
"""
import pytest
from django.core.exceptions import ValidationError

from apps.campaigns.models import Campaign, CampaignEnrollment, CampaignStep
from apps.campaigns.services import CampaignService
from apps.leads.models import Lead
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='CRM Firm')


@pytest.fixture
def advisor(tenant):
    return CustomUser.objects.create_user(
        email='adv@firm.com', password='pass1234!',
        first_name='A', last_name='B',
        role=CustomUser.ROLE_ADVISOR, tenant=tenant,
    )


@pytest.fixture
def lead(tenant):
    return Lead.objects.create(
        tenant=tenant, first_name='John', last_name='Doe',
        email='john@example.com', source=Lead.SOURCE_MANUAL,
    )


@pytest.fixture
def campaign_draft(tenant, advisor):
    return Campaign.objects.create(tenant=tenant, name='Test Campaign', created_by=advisor)


@pytest.fixture
def campaign_with_step(campaign_draft):
    CampaignStep.objects.create(
        campaign=campaign_draft,
        step_number=1,
        channel=CampaignStep.CHANNEL_EMAIL,
        content_template='Hello {{name}}',
        delay_days=0,
    )
    return campaign_draft


@pytest.fixture
def active_campaign(campaign_with_step, advisor):
    return CampaignService.activate_campaign(campaign=campaign_with_step, actor=advisor)


@pytest.mark.django_db
class TestCampaignLifecycle:

    def test_create_campaign(self, tenant, advisor):
        campaign = CampaignService.create_campaign(
            tenant=tenant, actor=advisor, name='New Campaign',
            steps_data=[{'channel': 'email', 'content_template': 'Hi', 'delay_days': 0}],
        )
        assert campaign.status == Campaign.STATUS_DRAFT
        assert campaign.steps.count() == 1

    def test_activate_campaign(self, campaign_with_step, advisor):
        campaign = CampaignService.activate_campaign(campaign=campaign_with_step, actor=advisor)
        assert campaign.status == Campaign.STATUS_ACTIVE

    def test_bru_09_cannot_activate_empty_campaign(self, campaign_draft, advisor):
        """BRU-09: campaign with no steps cannot be activated."""
        with pytest.raises(ValidationError, match="no steps"):
            CampaignService.activate_campaign(campaign=campaign_draft, actor=advisor)

    def test_cannot_activate_non_draft(self, active_campaign, advisor):
        active_campaign.status = Campaign.STATUS_COMPLETED
        active_campaign.save()
        with pytest.raises(ValidationError):
            CampaignService.activate_campaign(campaign=active_campaign, actor=advisor)

    def test_pause_campaign(self, active_campaign, advisor):
        campaign = CampaignService.pause_campaign(campaign=active_campaign, actor=advisor)
        assert campaign.status == Campaign.STATUS_PAUSED

    def test_cannot_pause_draft(self, campaign_draft, advisor):
        with pytest.raises(ValidationError):
            CampaignService.pause_campaign(campaign=campaign_draft, actor=advisor)


@pytest.mark.django_db
class TestCampaignEnroll:

    def test_enroll_lead(self, active_campaign, lead, advisor):
        enrollment = CampaignService.enroll_subject(
            campaign=active_campaign, actor=advisor, lead=lead,
        )
        assert enrollment.status == CampaignEnrollment.STATUS_ACTIVE
        assert enrollment.lead == lead

    def test_bru_07_opted_out_lead_blocked(self, active_campaign, lead, advisor):
        """BRU-07: opted-out lead cannot be enrolled."""
        lead.opted_out = True
        lead.save()
        with pytest.raises(ValidationError, match="opted out"):
            CampaignService.enroll_subject(campaign=active_campaign, actor=advisor, lead=lead)

    def test_bru_19_suppressed_lead_blocked(self, active_campaign, lead, advisor):
        """BRU-19: suppressed lead cannot be enrolled."""
        lead.is_suppressed = True
        lead.save()
        with pytest.raises(ValidationError, match="suppressed"):
            CampaignService.enroll_subject(campaign=active_campaign, actor=advisor, lead=lead)

    def test_bru_03_no_duplicate_active_enrollment(self, active_campaign, lead, advisor):
        """BRU-03: cannot have two active enrollments for the same lead in the same campaign."""
        CampaignService.enroll_subject(campaign=active_campaign, actor=advisor, lead=lead)
        with pytest.raises(ValidationError, match="already has an active enrollment"):
            CampaignService.enroll_subject(campaign=active_campaign, actor=advisor, lead=lead)

    def test_cannot_enroll_into_non_active_campaign(self, campaign_draft, lead, advisor):
        with pytest.raises(ValidationError, match="active campaign"):
            CampaignService.enroll_subject(campaign=campaign_draft, actor=advisor, lead=lead)


@pytest.mark.django_db
class TestEnrollmentStop:

    def test_bru_21_stop_enrollment(self, active_campaign, lead, advisor):
        """BRU-21: manual stop sets status and stopped_reason."""
        enrollment = CampaignService.enroll_subject(
            campaign=active_campaign, actor=advisor, lead=lead,
        )
        stopped = CampaignService.stop_enrollment(
            enrollment=enrollment, actor=advisor, reason='manual',
        )
        assert stopped.status == CampaignEnrollment.STATUS_STOPPED
        assert stopped.stopped_reason == 'manual'

    def test_cannot_stop_already_stopped(self, active_campaign, lead, advisor):
        enrollment = CampaignService.enroll_subject(
            campaign=active_campaign, actor=advisor, lead=lead,
        )
        CampaignService.stop_enrollment(enrollment=enrollment, actor=advisor, reason='manual')
        enrollment.refresh_from_db()
        with pytest.raises(ValidationError, match="not active"):
            CampaignService.stop_enrollment(enrollment=enrollment, actor=advisor, reason='manual')

    def test_bru_17_stop_all_on_reply(self, tenant, active_campaign, lead, advisor):
        """BRU-17/21: reply stops all active enrollments for the lead."""
        # Create a second campaign
        c2 = Campaign.objects.create(tenant=tenant, name='Campaign 2', created_by=advisor)
        CampaignStep.objects.create(
            campaign=c2, step_number=1,
            channel=CampaignStep.CHANNEL_EMAIL,
            content_template='Hi again',
            delay_days=0,
        )
        CampaignService.activate_campaign(campaign=c2, actor=advisor)

        CampaignService.enroll_subject(campaign=active_campaign, actor=advisor, lead=lead)
        CampaignService.enroll_subject(campaign=c2, actor=advisor, lead=lead)

        count = CampaignService.stop_all_enrollments_for_subject(
            tenant=tenant, lead=lead, reason='response',
        )
        assert count == 2
        active = CampaignEnrollment.objects.filter(
            lead=lead, status=CampaignEnrollment.STATUS_ACTIVE,
        ).count()
        assert active == 0

    def test_bru_01_stop_all_scoped_to_tenant(self, tenant, active_campaign, lead, advisor):
        """BRU-01: stop_all only affects enrollments in the same tenant."""
        t2 = Tenant.objects.create(firm_name='Other Firm')
        lead2 = Lead.objects.create(
            tenant=t2, first_name='Jane', last_name='Other',
            email='jane@other.com', source=Lead.SOURCE_MANUAL,
        )
        advisor2 = CustomUser.objects.create_user(
            email='adv2@other.com', password='pass1234!',
            first_name='X', last_name='Y',
            role=CustomUser.ROLE_ADVISOR, tenant=t2,
        )
        c2 = Campaign.objects.create(tenant=t2, name='Campaign T2', created_by=advisor2)
        CampaignStep.objects.create(
            campaign=c2, step_number=1,
            channel=CampaignStep.CHANNEL_EMAIL,
            content_template='Hello',
            delay_days=0,
        )
        CampaignService.activate_campaign(campaign=c2, actor=advisor2)
        CampaignService.enroll_subject(campaign=c2, actor=advisor2, lead=lead2)

        # Stop enrollments in tenant 1 — tenant 2 enrollment must remain
        CampaignService.enroll_subject(campaign=active_campaign, actor=advisor, lead=lead)
        CampaignService.stop_all_enrollments_for_subject(
            tenant=tenant, lead=lead, reason='response',
        )

        t2_active = CampaignEnrollment.objects.filter(
            tenant=t2, status=CampaignEnrollment.STATUS_ACTIVE,
        ).count()
        assert t2_active == 1
