import logging

from config.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=2, default_retry_delay=60, queue='analytics',
          name='analytics.take_daily_snapshots')
def take_daily_snapshots(self):
    """
    FM-26: compute and persist firm + advisor snapshots for all active tenants.
    Called nightly by Celery beat. Idempotent via unique_together on AnalyticsSnapshot.
    """
    from apps.tenants.models import Tenant
    from apps.analytics.services import AnalyticsService
    from apps.users.models import CustomUser

    tenants = Tenant.objects.filter(status=Tenant.STATUS_ACTIVE)
    for tenant in tenants:
        try:
            AnalyticsService.take_firm_snapshot(tenant=tenant)
        except Exception as exc:
            logger.exception("Failed firm snapshot for tenant %d", tenant.pk)

        advisors = CustomUser.objects.filter(
            tenant=tenant,
            is_active=True,
            role__in=('advisor', 'team_lead', 'senior_advisor'),
        )
        for advisor in advisors:
            try:
                AnalyticsService.take_advisor_snapshot(tenant=tenant, advisor=advisor)
            except Exception as exc:
                logger.exception(
                    "Failed advisor snapshot for tenant %d advisor %d", tenant.pk, advisor.pk,
                )
