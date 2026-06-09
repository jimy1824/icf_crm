import logging
from django.db import transaction
from django.core.exceptions import ValidationError

from apps.territories.models import Territory, AdvisorTerritory
from apps.audit.services import AuditService
from apps.common.events import event_bus

logger = logging.getLogger(__name__)


class TerritoryService:

    @staticmethod
    @transaction.atomic
    def create_territory(*, tenant, name: str, description: str = '', actor=None) -> Territory:
        """Create a new territory within a tenant. BRU-01: scoped to tenant."""
        territory = Territory(
            tenant=tenant,
            name=name,
            description=description,
            is_active=True,
        )
        territory.full_clean()
        territory.save()

        AuditService.log(
            actor=actor, tenant=tenant,
            action='territory.created',
            entity_type='Territory', entity_id=territory.pk,
            after_state={'name': name},
        )
        return territory

    @staticmethod
    @transaction.atomic
    def update_territory(*, territory: Territory, name: str = None, description: str = None, actor=None) -> Territory:
        before = {'name': territory.name, 'description': territory.description}
        if name is not None:
            territory.name = name
        if description is not None:
            territory.description = description
        territory.full_clean()
        territory.save(update_fields=['name', 'description', 'updated_at'])

        AuditService.log(
            actor=actor, tenant=territory.tenant,
            action='territory.updated',
            entity_type='Territory', entity_id=territory.pk,
            before_state=before,
            after_state={'name': territory.name, 'description': territory.description},
        )
        return territory

    @staticmethod
    @transaction.atomic
    def deactivate_territory(*, territory: Territory, actor=None) -> Territory:
        """Soft-delete: set is_active=False. Historical data preserved."""
        if not territory.is_active:
            return territory
        territory.is_active = False
        territory.save(update_fields=['is_active', 'updated_at'])

        AuditService.log(
            actor=actor, tenant=territory.tenant,
            action='territory.deactivated',
            entity_type='Territory', entity_id=territory.pk,
        )
        return territory

    @staticmethod
    @transaction.atomic
    def assign_advisor(*, territory: Territory, advisor, actor=None) -> AdvisorTerritory:
        """
        Assign an advisor to a territory.
        BRU-01: advisor must belong to the same tenant as the territory.
        """
        if advisor.tenant_id != territory.tenant_id:
            raise ValidationError("BRU-01: Advisor and Territory must belong to the same tenant.")
        if not territory.is_active:
            raise ValidationError("Cannot assign advisor to an inactive territory.")
        if advisor.role not in {'advisor', 'team_lead'}:
            raise ValidationError("Only Advisors and Team Leads can be assigned to territories.")
        if not advisor.is_active:
            raise ValidationError("Cannot assign an inactive advisor to a territory.")

        assignment, created = AdvisorTerritory.objects.get_or_create(
            advisor=advisor,
            territory=territory,
            defaults={'assigned_by': actor},
        )
        if created:
            AuditService.log(
                actor=actor, tenant=territory.tenant,
                action='territory.advisor_assigned',
                entity_type='Territory', entity_id=territory.pk,
                after_state={'advisor_id': advisor.pk},
            )
        return assignment

    @staticmethod
    @transaction.atomic
    def remove_advisor(*, territory: Territory, advisor, actor=None) -> None:
        """Remove an advisor from a territory."""
        deleted, _ = AdvisorTerritory.objects.filter(
            advisor=advisor, territory=territory,
        ).delete()
        if deleted:
            AuditService.log(
                actor=actor, tenant=territory.tenant,
                action='territory.advisor_removed',
                entity_type='Territory', entity_id=territory.pk,
                before_state={'advisor_id': advisor.pk},
            )

    @staticmethod
    def resolve_or_warn(*, tenant, territory_name: str) -> 'Territory | None':
        """
        Find territory by name (case-insensitive). Returns None and writes a
        warning audit entry if not found. Does NOT raise — callers decide
        whether a missing territory is fatal.
        """
        if not territory_name:
            return None
        territory = Territory.objects.filter(
            tenant=tenant, name__iexact=territory_name, is_active=True,
        ).first()
        if territory is None:
            logger.warning(
                "territory.name_unresolved tenant=%s name=%r",
                tenant.pk, territory_name,
            )
            AuditService.log(
                actor=None, tenant=tenant,
                action='territory.name_unresolved',
                entity_type='Territory', entity_id=0,
                after_state={'territory_name': territory_name},
            )
        return territory

    @staticmethod
    def get_active_advisors_for_territory(*, territory: Territory):
        """Return active advisors assigned to the territory."""
        from apps.users.models import CustomUser
        return CustomUser.objects.filter(
            advisor_territories__territory=territory,
            is_active=True,
            tenant=territory.tenant,
        ).distinct()

    @staticmethod
    def distribute_lead(*, lead) -> None:
        """
        Determine the winning advisor for a lead using round-robin within the territory.
        This is called synchronously in tests; production callers use the Celery task.
        """
        territory = lead.territory
        if territory is None:
            return

        advisors = list(
            TerritoryService.get_active_advisors_for_territory(territory=territory)
        )
        if not advisors:
            TerritoryService._notify_no_advisor(lead=lead, territory=territory)
            return

        from apps.leads.models import Lead as LeadModel
        from django.db.models import Count
        counts = {
            a.pk: LeadModel.objects.filter(
                tenant=lead.tenant,
                territory=territory,
                assigned_advisors=a,
            ).count()
            for a in advisors
        }
        winner = min(advisors, key=lambda a: (counts[a.pk], str(a.pk)))

        from apps.leads.services import LeadService
        LeadService.assign_advisors(lead=lead, advisor_ids=[winner.pk])

        AuditService.log(
            actor=None, tenant=lead.tenant,
            action='lead.auto_assigned',
            entity_type='Lead', entity_id=lead.pk,
            after_state={
                'territory': territory.name,
                'advisor_id': winner.pk,
                'method': 'round_robin',
            },
        )
        event_bus.emit(
            'lead.auto_assigned',
            tenant_id=lead.tenant_id,
            lead_id=lead.pk,
            advisor_id=winner.pk,
            territory_id=territory.pk,
        )

    @staticmethod
    def _notify_no_advisor(*, lead, territory) -> None:
        """Notify all Tenant Admins when a territory has no active advisor."""
        from apps.users.models import CustomUser
        from apps.notifications.services import NotificationService

        admins = CustomUser.objects.filter(
            tenant=lead.tenant,
            role=CustomUser.ROLE_TENANT_ADMIN,
            is_active=True,
        )
        for admin in admins:
            try:
                NotificationService.notify(
                    tenant=lead.tenant,
                    recipient=admin,
                    event_type='territory.no_advisor',
                    entity_type='Territory',
                    entity_id=territory.pk,
                    channels=['in_app'],
                )
            except Exception:
                logger.exception(
                    "Failed to notify admin %s for territory.no_advisor", admin.pk
                )
        AuditService.log(
            actor=None, tenant=lead.tenant,
            action='territory.no_advisor_notification_sent',
            entity_type='Territory', entity_id=territory.pk,
            after_state={
                'territory_name': territory.name,
                'lead_id': lead.pk,
                'lead_email': lead.email,
            },
        )


class TerritoryAnalyticsService:

    @staticmethod
    def territory_summary(*, tenant, territory: Territory) -> dict:
        """Live KPIs for one territory."""
        from apps.leads.models import Lead
        from apps.campaigns.models import Campaign, CampaignEnrollment

        total_leads = Lead.objects.filter(tenant=tenant, territory=territory).count()
        assigned_leads = Lead.objects.filter(
            tenant=tenant, territory=territory,
            assigned_advisors__isnull=False,
        ).distinct().count()
        unassigned_leads = total_leads - assigned_leads

        active_advisors = AdvisorTerritory.objects.filter(
            territory=territory,
            advisor__is_active=True,
        ).count()

        active_campaigns = Campaign.objects.filter(
            tenant=tenant, territories=territory, status=Campaign.STATUS_ACTIVE,
        ).count()

        return {
            'territory': territory.name,
            'territory_id': territory.pk,
            'total_leads': total_leads,
            'assigned_leads': assigned_leads,
            'unassigned_leads': unassigned_leads,
            'active_advisors': active_advisors,
            'active_campaigns': active_campaigns,
        }

    @staticmethod
    def territory_weekly(*, tenant, territory: Territory) -> dict:
        """Current ISO-week analytics for a territory."""
        import datetime
        from apps.leads.models import Lead

        today = datetime.date.today()
        week_start = today - datetime.timedelta(days=today.weekday())
        week_label = f"{today.isocalendar()[0]}-W{today.isocalendar()[1]:02d}"

        total_leads = Lead.objects.filter(
            tenant=tenant, territory=territory,
            created_at__date__gte=week_start,
        ).count()
        assigned_leads = Lead.objects.filter(
            tenant=tenant, territory=territory,
            created_at__date__gte=week_start,
            assigned_advisors__isnull=False,
        ).distinct().count()
        conversions = Lead.objects.filter(
            tenant=tenant, territory=territory,
            status=Lead.STATUS_CLIENT,
            updated_at__date__gte=week_start,
        ).count()
        active_advisors = AdvisorTerritory.objects.filter(
            territory=territory, advisor__is_active=True,
        ).count()

        return {
            'territory': territory.name,
            'territory_id': territory.pk,
            'week': week_label,
            'total_leads': total_leads,
            'assigned_leads': assigned_leads,
            'unassigned_leads': total_leads - assigned_leads,
            'conversions': conversions,
            'active_advisors': active_advisors,
        }

    @staticmethod
    def advisor_territory_analytics(*, tenant, advisor) -> dict:
        """Per-advisor breakdown: territories, lead counts, active campaigns."""
        from apps.leads.models import Lead
        from apps.campaigns.models import Campaign

        assignments = AdvisorTerritory.objects.filter(
            advisor=advisor,
            territory__tenant=tenant,
            territory__is_active=True,
        ).select_related('territory')

        result = []
        for at in assignments:
            territory = at.territory
            leads_count = Lead.objects.filter(
                tenant=tenant, territory=territory, assigned_advisors=advisor,
            ).count()
            active_campaigns = Campaign.objects.filter(
                tenant=tenant, territories=territory, status=Campaign.STATUS_ACTIVE,
            ).count()
            result.append({
                'territory_id': territory.pk,
                'territory': territory.name,
                'leads_count': leads_count,
                'active_campaigns': active_campaigns,
            })

        return {
            'advisor_id': advisor.pk,
            'territories': result,
        }

    @staticmethod
    def graph_leads_per_territory(*, tenant) -> list:
        """Chart data: territory vs total lead count."""
        from apps.leads.models import Lead
        from django.db.models import Count

        rows = (
            Lead.objects
            .filter(tenant=tenant, territory__isnull=False, territory__is_active=True)
            .values('territory__name', 'territory_id')
            .annotate(lead_count=Count('pk'))
            .order_by('-lead_count')
        )
        return [
            {'territory': r['territory__name'], 'territory_id': r['territory_id'],
             'value': r['lead_count']}
            for r in rows
        ]

    @staticmethod
    def graph_advisors_per_territory(*, tenant) -> list:
        """Chart data: territory vs active advisor count."""
        from django.db.models import Count

        rows = (
            AdvisorTerritory.objects
            .filter(territory__tenant=tenant, territory__is_active=True, advisor__is_active=True)
            .values('territory__name', 'territory_id')
            .annotate(advisor_count=Count('advisor_id', distinct=True))
            .order_by('-advisor_count')
        )
        return [
            {'territory': r['territory__name'], 'territory_id': r['territory_id'],
             'value': r['advisor_count']}
            for r in rows
        ]

    @staticmethod
    def graph_weekly_trend(*, tenant, weeks: int = 8) -> list:
        """Chart data: weekly lead arrivals per territory for the last N weeks."""
        import datetime
        from apps.leads.models import Lead
        from django.db.models import Count

        today = datetime.date.today()
        cutoff = today - datetime.timedelta(weeks=weeks)

        rows = (
            Lead.objects
            .filter(
                tenant=tenant,
                territory__isnull=False,
                territory__is_active=True,
                created_at__date__gte=cutoff,
            )
            .extra(select={'week': "to_char(leads_lead.created_at, 'IYYY-\"W\"IW')"})
            .values('week', 'territory__name', 'territory_id')
            .annotate(leads=Count('pk'))
            .order_by('week', 'territory__name')
        )
        return [
            {
                'week': r['week'],
                'territory': r['territory__name'],
                'territory_id': r['territory_id'],
                'leads': r['leads'],
            }
            for r in rows
        ]

    @staticmethod
    def graph_campaign_performance(*, tenant) -> list:
        """Chart data: territory vs active campaigns and enrollments."""
        from apps.campaigns.models import Campaign, CampaignEnrollment

        territories = Territory.objects.filter(tenant=tenant, is_active=True)
        result = []
        for territory in territories:
            active_campaigns = Campaign.objects.filter(
                tenant=tenant, territories=territory, status=Campaign.STATUS_ACTIVE,
            ).count()
            enrollments = CampaignEnrollment.objects.filter(
                tenant=tenant,
                campaign__territories=territory,
                status=CampaignEnrollment.STATUS_ACTIVE,
            ).count()
            result.append({
                'territory': territory.name,
                'territory_id': territory.pk,
                'active_campaigns': active_campaigns,
                'active_enrollments': enrollments,
            })
        return result

    @staticmethod
    def graph_conversion_rate(*, tenant) -> list:
        """Chart data: territory conversion rate (converted / total leads)."""
        from apps.leads.models import Lead

        territories = Territory.objects.filter(tenant=tenant, is_active=True)
        result = []
        for territory in territories:
            total = Lead.objects.filter(tenant=tenant, territory=territory).count()
            converted = Lead.objects.filter(
                tenant=tenant, territory=territory, status=Lead.STATUS_CLIENT,
            ).count()
            rate = round(converted / total * 100, 1) if total else 0.0
            result.append({
                'territory': territory.name,
                'territory_id': territory.pk,
                'total_leads': total,
                'converted_leads': converted,
                'conversion_rate_pct': rate,
            })
        return result
