from apps.campaigns.models import Campaign, CampaignEnrollment, CampaignStep


def get_campaign_by_id(*, tenant, pk) -> Campaign | None:
    return Campaign.objects.filter(tenant=tenant, pk=pk).first()


def get_campaigns_for_tenant(*, tenant, status=None):
    qs = Campaign.objects.filter(tenant=tenant).select_related('created_by')
    if status:
        qs = qs.filter(status=status)
    return qs


def get_campaign_steps(*, campaign):
    return campaign.steps.order_by('step_number')


def get_active_enrollments(*, tenant):
    return CampaignEnrollment.objects.filter(
        tenant=tenant, status=CampaignEnrollment.STATUS_ACTIVE,
    ).select_related('campaign', 'lead')


def get_active_enrollments_for_subject(*, tenant, lead):
    return CampaignEnrollment.objects.filter(
        tenant=tenant, lead=lead, status=CampaignEnrollment.STATUS_ACTIVE,
    )


def get_enrollments_for_subject(*, tenant, lead):
    return (
        CampaignEnrollment.objects
        .filter(tenant=tenant, lead=lead)
        .select_related('campaign')
    )


def get_enrollment_by_id(*, tenant, pk) -> CampaignEnrollment | None:
    return CampaignEnrollment.objects.filter(tenant=tenant, pk=pk).select_related(
        'campaign', 'lead',
    ).first()
