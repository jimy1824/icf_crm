import logging
from config.celery import app

logger = logging.getLogger(__name__)


@app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    queue='leads',
    name='apps.territories.tasks.distribute_lead_to_territory',
)
def distribute_lead_to_territory(self, lead_id: int) -> None:
    """
    Async territory-based lead distribution.
    BRU-16: idempotent — re-running on an already-assigned lead is safe (assign_advisors uses .set()).
    Picks the advisor with the fewest current leads in the territory (round-robin).
    If no advisors are assigned to the territory, notifies all Tenant Admins.
    """
    try:
        from apps.leads.models import Lead
        try:
            lead = Lead.objects.select_related('tenant', 'territory').get(pk=lead_id)
        except Lead.DoesNotExist:
            logger.warning("distribute_lead_to_territory: Lead %s not found", lead_id)
            return

        if lead.territory is None:
            logger.info("distribute_lead_to_territory: Lead %s has no territory — skipping", lead_id)
            return

        from apps.territories.services import TerritoryService
        TerritoryService.distribute_lead(lead=lead)

    except Exception as exc:
        logger.exception("distribute_lead_to_territory: error for lead %s", lead_id)
        raise self.retry(exc=exc)
