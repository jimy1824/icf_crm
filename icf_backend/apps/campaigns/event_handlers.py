"""
Campaign event handlers — subscribed in CampaignsConfig.ready().
BRU-03/17/21: any inbound reply stops all active campaign enrollments for that subject.
BRU-07: opt-out event also stops enrollments.
"""
import logging

from apps.common.events import event_bus
from config.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, default_retry_delay=30, queue='campaigns',
          name='campaigns.handle_reply_received')
def handle_reply_received(self, *, event_name, tenant_id, communication_id=None,
                           lead_id=None, from_email=None, **kwargs) -> None:
    """BRU-03/17/21: stop-on-reply — all active enrollments stopped for the lead."""
    try:
        from apps.campaigns.models import CampaignEnrollment
        from apps.campaigns.services import CampaignService
        from apps.leads.models import Lead
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.filter(pk=tenant_id).first()
        if not tenant:
            return

        lead = Lead.objects.filter(pk=lead_id).first() if lead_id else None
        if lead:
            count = CampaignService.stop_all_enrollments_for_subject(
                tenant=tenant, lead=lead,
                reason=CampaignEnrollment.REASON_RESPONSE,
            )
            logger.info(
                "handle_reply_received: stopped %d enrollments (lead=%s)",
                count, lead_id,
            )
    except Exception as exc:
        logger.exception("handle_reply_received error")
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=30, queue='campaigns',
          name='campaigns.handle_sms_optout')
def handle_sms_optout(self, *, event_name, tenant_id, lead_id=None, **kwargs) -> None:
    """BRU-07/19: SMS opt-out stops all campaign enrollments for the lead."""
    try:
        from apps.campaigns.models import CampaignEnrollment
        from apps.campaigns.services import CampaignService
        from apps.leads.models import Lead
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.filter(pk=tenant_id).first()
        if not tenant:
            return

        lead = Lead.objects.filter(pk=lead_id).first() if lead_id else None
        if lead:
            CampaignService.stop_all_enrollments_for_subject(
                tenant=tenant, lead=lead,
                reason=CampaignEnrollment.REASON_OPT_OUT,
            )
    except Exception as exc:
        logger.exception("handle_sms_optout error")
        raise self.retry(exc=exc)


event_bus.subscribe('communication.reply_received', handle_reply_received)
event_bus.subscribe('communication.sms_optout', handle_sms_optout)
