import pytest
from apps.campaigns.models import Campaign, CampaignStep, CampaignEnrollment
from apps.tenants.models import Tenant
from apps.leads.models import Lead


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm')


@pytest.fixture
def campaign(tenant):
    return Campaign.objects.create(tenant=tenant, name='Welcome Series')


@pytest.fixture
def lead(tenant):
    return Lead.objects.create(
        tenant=tenant, first_name='Eve', last_name='Adams',
        email='eve@example.com', source=Lead.SOURCE_MANUAL,
    )


@pytest.mark.django_db
class TestCampaign:
    def test_create(self, campaign):
        assert campaign.status == Campaign.STATUS_DRAFT
        assert str(campaign) == 'Welcome Series'

    def test_unique_name_per_tenant(self, tenant):
        Campaign.objects.create(tenant=tenant, name='Dup')
        with pytest.raises(Exception):
            Campaign.objects.create(tenant=tenant, name='Dup')


@pytest.mark.django_db
class TestCampaignStep:
    def test_steps_ordered_by_number(self, campaign):
        CampaignStep.objects.create(
            campaign=campaign, step_number=2,
            channel=CampaignStep.CHANNEL_EMAIL,
            content_template='Follow up', delay_days=3,
        )
        CampaignStep.objects.create(
            campaign=campaign, step_number=1,
            channel=CampaignStep.CHANNEL_EMAIL,
            content_template='Welcome', delay_days=0,
        )
        steps = list(campaign.steps.all())
        assert steps[0].step_number == 1
        assert steps[1].step_number == 2


@pytest.mark.django_db
class TestCampaignEnrollment:
    def test_requires_lead(self, campaign, tenant):
        """Every enrollment must reference a Lead (the single entity for all funnel stages)."""
        with pytest.raises(Exception):
            CampaignEnrollment.objects.create(
                campaign=campaign, tenant=tenant,
                lead=None,
            )

    def test_enroll_lead(self, campaign, tenant, lead):
        enrollment = CampaignEnrollment.objects.create(
            campaign=campaign, tenant=tenant, lead=lead
        )
        assert enrollment.status == CampaignEnrollment.STATUS_ACTIVE
        assert enrollment.current_step == 0
