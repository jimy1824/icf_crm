"""
Reusable queryset selectors for CampaignExecutionTimeline.
BRU-01: every selector accepts tenant and filters by it.
"""
from django.utils import timezone as dj_tz


def get_timeline_for_lead(*, tenant, lead):
    from apps.campaign_timeline.models import CampaignExecutionTimeline
    return (
        CampaignExecutionTimeline.objects
        .filter(tenant=tenant, lead=lead)
        .select_related('campaign', 'campaign_step')
        .order_by('step_order', 'scheduled_at')
    )


def get_timeline_for_campaign(*, tenant, campaign):
    from apps.campaign_timeline.models import CampaignExecutionTimeline
    return (
        CampaignExecutionTimeline.objects
        .filter(tenant=tenant, campaign=campaign)
        .select_related('lead', 'campaign_step')
        .order_by('scheduled_at')
    )


def get_timeline_for_enrollment(*, tenant, enrollment):
    from apps.campaign_timeline.models import CampaignExecutionTimeline
    return (
        CampaignExecutionTimeline.objects
        .filter(tenant=tenant, enrollment=enrollment)
        .select_related('campaign_step')
        .order_by('step_order')
    )


def get_advisor_timeline(*, tenant, advisor, hours_ahead: int = 48):
    from apps.campaign_timeline.models import CampaignExecutionTimeline
    import datetime
    now = dj_tz.now()
    cutoff = now + datetime.timedelta(hours=hours_ahead)
    return (
        CampaignExecutionTimeline.objects
        .filter(
            tenant=tenant,
            lead__assigned_advisors=advisor,
            status=CampaignExecutionTimeline.STATUS_PENDING,
            scheduled_at__range=(now, cutoff),
        )
        .select_related('lead', 'campaign', 'campaign_step')
        .order_by('scheduled_at')
    )


def get_pending_due_entries(*, tenant=None):
    """All Pending entries with scheduled_at <= now(). Optionally scoped to tenant."""
    from apps.campaign_timeline.models import CampaignExecutionTimeline
    qs = CampaignExecutionTimeline.objects.filter(
        status=CampaignExecutionTimeline.STATUS_PENDING,
        scheduled_at__lte=dj_tz.now(),
    )
    if tenant:
        qs = qs.filter(tenant=tenant)
    return qs.order_by('scheduled_at')
