import logging
from datetime import timedelta

from django.utils import timezone

from config.celery import app

logger = logging.getLogger(__name__)

# BRU-09: quiet hours — no automated sends between 9 PM and 8 AM
QUIET_HOUR_START = 21
QUIET_HOUR_END = 8


def _is_quiet_hour() -> bool:
    now = timezone.localtime(timezone.now())
    hour = now.hour
    return hour >= QUIET_HOUR_START or hour < QUIET_HOUR_END


def _next_quiet_hour_end() -> object:
    """Return the datetime of the next 8 AM."""
    now = timezone.localtime(timezone.now())
    next_send = now.replace(hour=QUIET_HOUR_END, minute=0, second=0, microsecond=0)
    if now.hour >= QUIET_HOUR_END:
        next_send += timedelta(days=1)
    return next_send


@app.task(bind=True, max_retries=3, default_retry_delay=60, queue='campaigns',
          name='campaigns.advance_enrollment')
def advance_enrollment(self, enrollment_id: int) -> None:
    """
    Determine the next step for an enrollment and schedule execute_campaign_step.
    BRU-03: stops if enrollment status is no longer active.
    BRU-09: defers until after quiet hours.
    """
    try:
        from apps.campaigns.models import CampaignEnrollment, CampaignStep
        try:
            enrollment = CampaignEnrollment.objects.select_related(
                'campaign', 'lead',
            ).get(pk=enrollment_id)
        except CampaignEnrollment.DoesNotExist:
            logger.warning("advance_enrollment: enrollment %d not found", enrollment_id)
            return

        if enrollment.status != CampaignEnrollment.STATUS_ACTIVE:
            logger.info(
                "advance_enrollment: enrollment %d is %s — skipping",
                enrollment_id, enrollment.status,
            )
            return

        next_step_number = enrollment.current_step + 1
        try:
            step = CampaignStep.objects.get(
                campaign=enrollment.campaign,
                step_number=next_step_number,
            )
        except CampaignStep.DoesNotExist:
            # No more steps — mark completed
            enrollment.status = CampaignEnrollment.STATUS_COMPLETED
            enrollment.stopped_reason = CampaignEnrollment.REASON_COMPLETED
            enrollment.save(update_fields=['status', 'stopped_reason', 'updated_at'])
            logger.info("advance_enrollment: enrollment %d completed", enrollment_id)
            return

        # BRU-09: quiet hours deferral
        if step.delay_days == 0 and _is_quiet_hour():
            eta = _next_quiet_hour_end()
            execute_campaign_step.apply_async(args=[enrollment_id, step.pk], eta=eta)
            logger.info(
                "advance_enrollment: enrollment %d deferred to %s (quiet hours)",
                enrollment_id, eta,
            )
            return

        # Schedule with delay
        eta = timezone.now() + timedelta(days=step.delay_days)
        if _is_quiet_hour():
            eta = max(eta, _next_quiet_hour_end())
        execute_campaign_step.apply_async(args=[enrollment_id, step.pk], eta=eta)

    except Exception as exc:
        logger.exception("advance_enrollment error for enrollment %d", enrollment_id)
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=30, queue='campaigns',
          name='campaigns.execute_campaign_step')
def execute_campaign_step(self, enrollment_id: int, step_id: int) -> None:
    """
    Execute one campaign step.
    E-1  (BRU-05): abort and re-queue if advisor mailbox is suspended/expired.
    E-3  (BRU-03): atomic select_for_update prevents stop-on-reply race.
    BRU-07: skip if opted out.
    BRU-18/19: suppression check before send.
    """
    from django.db import transaction as _tx
    try:
        from apps.campaigns.models import CampaignEnrollment, CampaignStep
        from apps.communications.services import CommunicationService
        from apps.common.edge_cases import assert_mailbox_active
        from django.core.exceptions import ValidationError as DjValidationError

        # E-3: atomic read of enrollment status to close the reply-race window
        with _tx.atomic():
            try:
                enrollment = (
                    CampaignEnrollment.objects
                    .select_for_update()
                    .select_related('campaign', 'lead', 'tenant')
                    .get(pk=enrollment_id)
                )
            except CampaignEnrollment.DoesNotExist:
                logger.warning("execute_campaign_step: enrollment %d not found", enrollment_id)
                return

            # BRU-03 / E-3: inside the lock — guaranteed latest status
            if enrollment.status != CampaignEnrollment.STATUS_ACTIVE:
                logger.info(
                    "execute_campaign_step: enrollment %d stopped (%s) — aborting step %d",
                    enrollment_id, enrollment.status, step_id,
                )
                return

            # BRU-07: opt-out check (also inside lock to avoid TOCTOU)
            if enrollment.lead and (
                enrollment.lead.opted_out or enrollment.lead.is_suppressed
            ):
                enrollment.status = CampaignEnrollment.STATUS_STOPPED
                enrollment.stopped_reason = CampaignEnrollment.REASON_OPT_OUT
                enrollment.save(update_fields=['status', 'stopped_reason', 'updated_at'])
                logger.info(
                    "execute_campaign_step: lead opted out — stopped enrollment %d",
                    enrollment_id,
                )
                return

            try:
                step = CampaignStep.objects.get(pk=step_id)
            except CampaignStep.DoesNotExist:
                logger.warning("execute_campaign_step: step %d not found", step_id)
                return

            tenant = enrollment.tenant
            lead = enrollment.lead

            # E-1 (BRU-05): check advisor's mailbox is active before email steps
            if step.channel == CampaignStep.CHANNEL_EMAIL:
                from apps.communications.models import MailboxConnection
                advisor = enrollment.campaign.created_by
                if advisor:
                    conn = MailboxConnection.objects.filter(
                        advisor=advisor,
                        tenant=tenant,
                        status=MailboxConnection.STATUS_ACTIVE,
                    ).first()
                    if conn:
                        try:
                            assert_mailbox_active(conn)
                        except DjValidationError:
                            # BRU-05: suspend automation, re-queue after reconnect
                            from apps.communications.services import MailboxService
                            MailboxService.suspend_on_token_expiry(connection=conn)
                            # Re-queue this step for later — Celery countdown 1 hour
                            logger.warning(
                                "execute_campaign_step: mailbox suspended (E-1) — "
                                "re-queuing enrollment %d step %d in 1h",
                                enrollment_id, step_id,
                            )
                            execute_campaign_step.apply_async(
                                args=[enrollment_id, step_id], countdown=3600,
                            )
                            return

            # BRU-18: suppression check
            if step.channel == CampaignStep.CHANNEL_EMAIL:
                if lead and lead.email and CommunicationService.is_suppressed_email(
                    tenant=tenant, email=lead.email,
                ):
                    enrollment.status = CampaignEnrollment.STATUS_STOPPED
                    enrollment.stopped_reason = CampaignEnrollment.REASON_OPT_OUT
                    enrollment.save(update_fields=['status', 'stopped_reason', 'updated_at'])
                    logger.info(
                        "execute_campaign_step: email suppressed — stopped enrollment %d",
                        enrollment_id,
                    )
                    return

            elif step.channel == CampaignStep.CHANNEL_SMS:
                if lead and lead.phone and CommunicationService.is_suppressed_phone(
                    tenant=tenant, phone=lead.phone,
                ):
                    enrollment.status = CampaignEnrollment.STATUS_STOPPED
                    enrollment.stopped_reason = CampaignEnrollment.REASON_OPT_OUT
                    enrollment.save(update_fields=['status', 'stopped_reason', 'updated_at'])
                    return

            # Record the outbound communication (BRU-16: idempotent external_id)
            external_id = f"campaign-{enrollment_id}-step-{step.step_number}"
            CommunicationService.record_communication(
                tenant=tenant,
                channel=step.channel,
                direction='outbound',
                body_ref=step.content_template[:500],
                external_id=external_id,
                lead=lead,
                subject=step.subject,
                campaign_enrollment=enrollment,
            )

            # Advance step counter
            enrollment.current_step = step.step_number
            enrollment.save(update_fields=['current_step', 'updated_at'])

        # Schedule next step (outside the lock)
        advance_enrollment.delay(enrollment_id)

    except Exception as exc:
        logger.exception(
            "execute_campaign_step error for enrollment %d step %d", enrollment_id, step_id,
        )
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=30, queue='campaigns',
          name='campaigns.handle_reply_received')
def handle_reply_received(self, *, event_name, tenant_id, communication_id=None,
                           lead_id=None, **kwargs) -> None:
    """
    BRU-03/17/21: on any inbound reply, stop all active campaign enrollments for the lead.
    Idempotent — calling twice is safe (already-stopped enrollments are filtered out).
    """
    try:
        from apps.campaigns.services import CampaignService
        from apps.leads.models import Lead
        from apps.tenants.models import Tenant

        try:
            tenant = Tenant.objects.get(pk=tenant_id)
        except Tenant.DoesNotExist:
            return

        lead = Lead.objects.filter(pk=lead_id).first() if lead_id else None
        if lead:
            count = CampaignService.stop_all_enrollments_for_subject(
                tenant=tenant,
                lead=lead,
                reason=CampaignEnrollment.REASON_RESPONSE,
            )
            logger.info(
                "handle_reply_received: stopped %d enrollments for lead=%s",
                count, lead_id,
            )
    except Exception as exc:
        logger.exception("handle_reply_received error")
        raise self.retry(exc=exc)


# Deferred import to avoid circular reference
from apps.campaigns.models import CampaignEnrollment  # noqa: E402
