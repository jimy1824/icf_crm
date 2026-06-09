"""
FM-12 Dashboard selectors — tenant-scoped querysets for the dashboard API views.
All selectors are BRU-01 safe: every queryset is filtered by tenant before return.
Callers pass the resolved objects (tenant, advisor); selectors never touch request.
"""
from datetime import date

from django.db.models import Count, Prefetch, Q


def get_tenant_advisors(*, tenant):
    """
    GET /api/v1/analytics/advisors/
    Returns active users whose role is advisor or team_lead, scoped to tenant.
    Annotated with active_lead_count for display.
    BRU-01: strict tenant filter.
    """
    from apps.users.models import CustomUser
    from apps.leads.models import Lead

    return (
        CustomUser.objects.filter(
            tenant=tenant,
            is_active=True,
            role__in=[CustomUser.ROLE_ADVISOR, CustomUser.ROLE_TEAM_LEAD],
        )
        .annotate(
            active_lead_count=Count(
                'assigned_leads',
                filter=Q(assigned_leads__tenant=tenant),
                distinct=True,
            )
        )
        .order_by('first_name', 'last_name')
    )


def get_today_leads_queryset(*, tenant, advisor=None, on_date=None, search=None):
    """
    Optimised queryset for Today's Leads table.
    Returns a QuerySet (not a list) so DRF pagination / ordering / search filters work.
    select_related + prefetch_related prevent N+1 on Territory, Advisors, Campaign.
    BRU-01: always filtered by tenant.
    """
    from apps.leads.models import Lead
    from apps.campaigns.models import CampaignEnrollment

    target_date = on_date or date.today()

    active_enrollment_prefetch = Prefetch(
        'campaign_enrollments',
        queryset=(
            CampaignEnrollment.objects.filter(status='active')
            .select_related('campaign')
            .order_by('-created_at')
        ),
        to_attr='active_enrollments',
    )

    qs = (
        Lead.objects.filter(tenant=tenant, created_at__date=target_date)
        .select_related('territory')
        .prefetch_related('assigned_advisors', active_enrollment_prefetch)
        .distinct()
    )

    if advisor:
        qs = qs.filter(assigned_advisors=advisor)

    if search:
        qs = qs.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
        )

    return qs


def get_today_activities_queryset(*, tenant, advisor=None, on_date=None, search=None):
    """
    Optimised queryset for Today's Scheduled Activities table.
    Returns a QuerySet so DRF pagination / ordering / search filters work.
    BRU-01: always filtered by tenant.
    """
    from apps.campaign_timeline.models import CampaignExecutionTimeline

    target_date = on_date or date.today()

    qs = (
        CampaignExecutionTimeline.objects.filter(
            tenant=tenant,
            scheduled_at__date=target_date,
        )
        .select_related('lead', 'lead__territory', 'campaign', 'campaign_step')
        .prefetch_related('lead__assigned_advisors')
    )

    if advisor:
        qs = qs.filter(lead__assigned_advisors=advisor)

    if search:
        qs = qs.filter(
            Q(lead__first_name__icontains=search)
            | Q(lead__last_name__icontains=search)
            | Q(campaign__name__icontains=search)
        )

    return qs
