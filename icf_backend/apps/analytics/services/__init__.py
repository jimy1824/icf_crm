"""
FM-12/FM-26: Analytics aggregation service.
Four-level dashboards: platform / firm / advisor / client.
BRU-01: all queries scoped per tenant.
Snapshots written once per day by Celery beat (idempotent via unique_together).
"""
import logging
from datetime import date, timedelta, datetime

from apps.analytics.models import AnalyticsSnapshot

logger = logging.getLogger(__name__)


class AnalyticsService:

    # ------------------------------------------------------------------
    # Dashboard data — live aggregation (for API responses)
    # ------------------------------------------------------------------

    @staticmethod
    def firm_dashboard(*, tenant) -> dict:
        """FM-12: firm-level KPIs for Tenant Admin / Team Lead."""
        from apps.leads.models import Lead
        from apps.campaigns.models import Campaign, CampaignEnrollment
        from apps.communications.models import Communication

        leads_total = Lead.objects.filter(tenant=tenant).count()
        leads_converted = Lead.objects.filter(
            tenant=tenant, status__in=Lead.CLIENT_STATUSES,
        ).count()
        conversion_rate = (
            round(leads_converted / leads_total * 100, 1) if leads_total else 0.0
        )

        active_campaigns = Campaign.objects.filter(
            tenant=tenant, status=Campaign.STATUS_ACTIVE,
        ).count()
        active_enrollments = CampaignEnrollment.objects.filter(
            tenant=tenant, status=CampaignEnrollment.STATUS_ACTIVE,
        ).count()
        comms_last_30 = Communication.objects.filter(
            tenant=tenant,
            created_at__date__gte=date.today() - timedelta(days=30),
        ).count()

        return {
            'leads': {
                'total': leads_total,
                'converted': leads_converted,
                'conversion_rate_pct': conversion_rate,
            },
            'campaigns': {
                'active': active_campaigns,
                'active_enrollments': active_enrollments,
            },
            'communications': {
                'last_30_days': comms_last_30,
            },
        }

    @staticmethod
    def advisor_dashboard(*, tenant, advisor) -> dict:
        """
        FM-12: advisor-level KPIs scoped to their own leads/clients.
        Extended to include pipeline_stages and active_campaigns
        so the tenant CRM dashboard can render all widgets from a single call.
        """
        from apps.leads.models import Lead
        from apps.communications.models import Communication, Meeting
        from apps.campaigns.models import Campaign, CampaignEnrollment
        from django.db.models import Count

        my_leads_qs = Lead.objects.filter(tenant=tenant, assigned_advisors=advisor)
        my_leads = my_leads_qs.exclude(status__in=Lead.CLIENT_STATUSES).count()
        my_clients = my_leads_qs.filter(status__in=Lead.CLIENT_STATUSES).count()
        my_comms_30d = Communication.objects.filter(
            tenant=tenant, sent_by=advisor,
            created_at__date__gte=date.today() - timedelta(days=30),
        ).count()
        upcoming_meetings = Meeting.objects.filter(
            tenant=tenant, advisor=advisor,
            scheduled_at__date__gte=date.today(),
        ).count()

        # Conversion rate: leads that became clients / total ever assigned to this advisor
        all_my = Lead.objects.filter(tenant=tenant, assigned_advisors=advisor).count()
        converted = Lead.objects.filter(
            tenant=tenant, assigned_advisors=advisor, status=Lead.STATUS_CLIENT,
        ).count()
        conversion_rate = round(converted / all_my * 100, 1) if all_my else 0.0

        # Active campaigns the advisor is part of (via enrollments on their leads)
        active_campaigns = CampaignEnrollment.objects.filter(
            tenant=tenant,
            lead__in=my_leads_qs,
            status=CampaignEnrollment.STATUS_ACTIVE,
        ).values('campaign').distinct().count()

        # Pipeline stages — grouped by pipeline_stage for bar chart
        stage_counts = (
            my_leads_qs
            .values('pipeline_stage')
            .annotate(count=Count('id'))
        )
        pipeline_stages = [
            {'stage': row['pipeline_stage'], 'count': row['count']}
            for row in stage_counts
        ]

        return {
            # Correct keys (frontend was using wrong names)
            'my_leads': my_leads,
            'my_clients': my_clients,
            'communications_last_30_days': my_comms_30d,
            'upcoming_meetings': upcoming_meetings,
            'conversion_rate': conversion_rate,
            'active_campaigns': active_campaigns,
            # Chart data
            'pipeline_stages': pipeline_stages,
        }

    @staticmethod
    def firm_dashboard_extended(*, tenant) -> dict:
        """
        Extended firm dashboard — same KPIs as firm_dashboard plus
        pipeline_stages breakdown and advisor breakdown for analytics page.
        """
        from apps.leads.models import Lead
        from apps.campaigns.models import Campaign, CampaignEnrollment
        from apps.communications.models import Communication
        from apps.users.models import CustomUser
        from django.db.models import Count

        base = AnalyticsService.firm_dashboard(tenant=tenant)

        # Pipeline stages firm-wide
        stage_counts = (
            Lead.objects.filter(tenant=tenant)
            .values('pipeline_stage')
            .annotate(count=Count('id'))
        )
        pipeline_stages = [
            {'stage': row['pipeline_stage'], 'count': row['count']}
            for row in stage_counts
        ]

        # Advisor breakdown (clients per advisor, for bar chart)
        from apps.leads.models import Lead as LeadModel
        advisors = CustomUser.objects.filter(
            tenant=tenant,
            role__in=['advisor', 'team_lead'],
            is_active=True,
        ).values('id', 'first_name', 'last_name')

        advisor_breakdown = []
        for a in advisors:
            count = LeadModel.objects.filter(
                tenant=tenant,
                assigned_advisors__id=a['id'],
                status__in=LeadModel.CLIENT_STATUSES,
            ).distinct().count()
            advisor_breakdown.append({
                'advisor_name': f"{a['first_name']} {a['last_name']}",
                'client_count': count,
            })

        base['pipeline_stages'] = pipeline_stages
        base['advisor_breakdown'] = advisor_breakdown
        return base

    @staticmethod
    def weekly_lead_analytics(*, tenant, days=7, advisor=None) -> list:
        """
        Dashboard Section 1: stacked bar chart data.
        Returns one entry per date for the last `days` days.
        Each entry: { date, received, responded }
        responded = leads that have at least one inbound Communication (is_reply=True).
        BRU-01: scoped to tenant; optional advisor filter.
        """
        from apps.leads.models import Lead
        from apps.communications.models import Communication
        from django.db.models import Count

        today = date.today()
        start = today - timedelta(days=days - 1)

        lead_qs = Lead.objects.filter(tenant=tenant, created_at__date__gte=start)
        if advisor:
            lead_qs = lead_qs.filter(assigned_advisors=advisor)

        # Leads received per day
        received_map = dict(
            lead_qs.values('created_at__date')
            .annotate(c=Count('id'))
            .values_list('created_at__date', 'c')
        )

        # Leads that got an inbound reply per day (grouped by lead creation date)
        responded_leads = Communication.objects.filter(
            tenant=tenant,
            is_reply=True,
            lead__in=lead_qs,
        ).values('lead_id').distinct()

        # Group those leads by their creation date
        responded_map = dict(
            lead_qs.filter(id__in=responded_leads.values('lead_id'))
            .values('created_at__date')
            .annotate(c=Count('id'))
            .values_list('created_at__date', 'c')
        )

        result = []
        for i in range(days):
            d = start + timedelta(days=i)
            result.append({
                'date': d.strftime('%b %d'),
                'received': received_map.get(d, 0),
                'responded': responded_map.get(d, 0),
            })
        return result

    @staticmethod
    def today_leads(*, tenant, advisor=None, on_date=None) -> list:
        """
        Dashboard Section 2: today's leads table.
        BRU-01: tenant-scoped. Optional advisor filter.
        """
        from apps.leads.models import Lead
        from apps.users.models import CustomUser

        target_date = on_date or date.today()
        qs = (
            Lead.objects.filter(tenant=tenant, created_at__date=target_date)
            .select_related('territory')
            .prefetch_related('assigned_advisors', 'campaign_enrollments__campaign')
            .order_by('-created_at')
        )
        if advisor:
            qs = qs.filter(assigned_advisors=advisor)

        results = []
        for lead in qs:
            advisors = list(lead.assigned_advisors.all())
            advisor_name = (
                f"{advisors[0].first_name} {advisors[0].last_name}"
                if advisors else 'Unassigned'
            )
            # Most recent active campaign enrollment
            enrollment = (
                lead.campaign_enrollments
                .filter(status='active')
                .select_related('campaign')
                .first()
            )
            results.append({
                'id': lead.id,
                'name': f"{lead.first_name} {lead.last_name}",
                'territory': lead.territory.name if lead.territory else '—',
                'advisor': advisor_name,
                'campaign': enrollment.campaign.name if enrollment else '—',
                'status': lead.pipeline_stage,
                'created_at': lead.created_at.strftime('%H:%M'),
            })
        return results

    @staticmethod
    def today_activities(*, tenant, advisor=None, on_date=None) -> list:
        """
        Dashboard Section 3: today's scheduled campaign activities (timeline entries).
        BRU-01: tenant-scoped.
        """
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        from django.utils import timezone

        target_date = on_date or date.today()
        qs = (
            CampaignExecutionTimeline.objects.filter(
                tenant=tenant,
                scheduled_at__date=target_date,
            )
            .select_related('lead', 'campaign', 'campaign_step')
            .order_by('scheduled_at')
        )
        if advisor:
            qs = qs.filter(lead__assigned_advisors=advisor)

        results = []
        for entry in qs:
            results.append({
                'id': entry.id,
                'lead_name': (
                    f"{entry.lead.first_name} {entry.lead.last_name}"
                    if entry.lead else '—'
                ),
                'campaign_name': entry.campaign.name if entry.campaign else '—',
                'step_order': entry.step_order,
                'step_type': entry.step_type,
                'scheduled_at': entry.scheduled_at.strftime('%H:%M'),
                'status': entry.status,
            })
        return results

    @staticmethod
    def today_responses(*, tenant, advisor=None, on_date=None) -> list:
        """
        Dashboard Section 4: inbound replies received today.
        is_reply=True marks a Communication as a response (BRU-17).
        BRU-01: tenant-scoped.
        """
        from apps.communications.models import Communication

        target_date = on_date or date.today()
        qs = (
            Communication.objects.filter(
                tenant=tenant,
                is_reply=True,
                created_at__date=target_date,
            )
            .select_related('lead', 'sent_by')
            .order_by('-created_at')
        )
        if advisor:
            qs = qs.filter(
                lead__assigned_advisors=advisor,
            )

        results = []
        for comm in qs:
            lead = comm.lead
            lead_name = (
                f"{lead.first_name} {lead.last_name}" if lead else '—'
            )
            advisor_obj = comm.sent_by
            advisor_name = (
                f"{advisor_obj.first_name} {advisor_obj.last_name}"
                if advisor_obj else '—'
            )
            results.append({
                'id': comm.id,
                'lead_name': lead_name,
                'advisor': advisor_name,
                'response_type': comm.channel,
                'message_preview': comm.subject[:120] if comm.subject else '—',
                'received_at': comm.created_at.strftime('%H:%M'),
            })
        return results

    @staticmethod
    def territory_lead_distribution(*, tenant, days=7) -> list:
        """
        Dashboard Section 5: horizontal bar chart — leads per territory.
        Returns territories ordered by lead count descending.
        BRU-01: tenant-scoped.
        """
        from apps.leads.models import Lead
        from apps.territories.models import Territory
        from django.db.models import Count

        start = date.today() - timedelta(days=days - 1)
        territory_counts = (
            Lead.objects.filter(tenant=tenant, territory__isnull=False, created_at__date__gte=start)
            .values('territory__id', 'territory__name')
            .annotate(lead_count=Count('id'))
            .order_by('-lead_count')
        )

        return [
            {
                'territory': row['territory__name'],
                'territory_id': row['territory__id'],
                'lead_count': row['lead_count'],
            }
            for row in territory_counts
        ]

    @staticmethod
    def client_dashboard(*, tenant, lead) -> dict:
        """FM-12: client-level KPIs — goals, meetings. lead IS the client entity."""
        from apps.financials.models import FinancialGoal, FinancialProfile
        from apps.communications.models import Meeting

        goals = FinancialGoal.objects.filter(tenant=tenant, lead=lead)
        total_goals = goals.count()
        on_track = goals.filter(is_off_track=False).count()
        off_track = goals.filter(is_off_track=True).count()

        net_worth = None
        try:
            profile = FinancialProfile.objects.get(tenant=tenant, lead=lead)
            net_worth = float(profile.net_worth)
        except Exception:
            pass

        upcoming_meetings = Meeting.objects.filter(
            tenant=tenant, lead=lead,
            scheduled_at__date__gte=date.today(),
        ).count()

        return {
            'goals': {
                'total': total_goals,
                'on_track': on_track,
                'off_track': off_track,
            },
            'net_worth': net_worth,
            'upcoming_meetings': upcoming_meetings,
        }

    @staticmethod
    def platform_dashboard() -> dict:
        """FM-12: super-admin platform-wide KPIs (cross-tenant aggregate)."""
        from django.db.models import Count
        from apps.tenants.models import Tenant, TenantSubscription
        from apps.leads.models import Lead
        from apps.users.models import CustomUser

        total_tenants = Tenant.objects.filter(status=Tenant.STATUS_ACTIVE).count()
        total_leads = Lead.objects.count()
        total_users = CustomUser.objects.filter(is_active=True).count()
        subs_by_status = dict(
            TenantSubscription.objects.values_list('status').annotate(c=Count('pk'))
        )
        return {
            'active_tenants': total_tenants,
            'total_leads': total_leads,
            'total_active_users': total_users,
            'subscriptions_by_status': subs_by_status,
        }

    # ------------------------------------------------------------------
    # Snapshot persistence (called by Celery beat, idempotent)
    # ------------------------------------------------------------------

    @staticmethod
    def take_firm_snapshot(*, tenant, snapshot_date: date | None = None) -> AnalyticsSnapshot:
        """FM-26: persist firm-level metrics for the given date."""
        d = snapshot_date or date.today()
        metrics = AnalyticsService.firm_dashboard(tenant=tenant)
        snapshot, _ = AnalyticsSnapshot.objects.update_or_create(
            tenant=tenant,
            snapshot_date=d,
            level=AnalyticsSnapshot.LEVEL_FIRM,
            entity_id='',
            defaults={'metrics': metrics},
        )
        return snapshot

    @staticmethod
    def take_advisor_snapshot(*, tenant, advisor, snapshot_date: date | None = None) -> AnalyticsSnapshot:
        d = snapshot_date or date.today()
        metrics = AnalyticsService.advisor_dashboard(tenant=tenant, advisor=advisor)
        snapshot, _ = AnalyticsSnapshot.objects.update_or_create(
            tenant=tenant,
            snapshot_date=d,
            level=AnalyticsSnapshot.LEVEL_ADVISOR,
            entity_id=str(advisor.pk),
            defaults={'metrics': metrics},
        )
        return snapshot
