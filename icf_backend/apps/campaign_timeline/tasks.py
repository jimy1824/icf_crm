"""
Campaign Timeline Celery tasks.

execute_timeline_step
    Executes a single CampaignExecutionTimeline entry.
    Workers call this after fetching status=Pending, scheduled_at<=now().

poll_due_timeline_entries
    Periodic beat task: finds all due Pending entries and dispatches
    execute_timeline_step for each.
    This replaces the old advance_enrollment / execute_campaign_step pair
    for enrollments that use the timeline system.
"""
import logging

from config.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=5, default_retry_delay=60, queue='campaigns',
          name='apps.campaign_timeline.tasks.execute_timeline_step')
def execute_timeline_step(self, entry_id: int) -> None:
    """
    Execute one timeline entry.
    BRU-16: idempotent — TimelineService.execute_entry handles double-call safely.
    """
    try:
        from apps.campaign_timeline.services import TimelineService
        executed = TimelineService.execute_entry(entry_id=entry_id)
        if executed:
            logger.info("execute_timeline_step: entry %d executed", entry_id)
        else:
            logger.info("execute_timeline_step: entry %d skipped/no-op", entry_id)
    except Exception as exc:
        logger.exception("execute_timeline_step error for entry %d", entry_id)
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=1, default_retry_delay=30, queue='campaigns',
          name='apps.campaign_timeline.tasks.poll_due_timeline_entries')
def poll_due_timeline_entries(self) -> None:
    """
    Periodic beat task (runs every minute via Celery Beat).
    Fetches all Pending timeline entries whose scheduled_at <= now()
    and dispatches execute_timeline_step for each.

    Workers never recalculate intervals — scheduled_at was computed at
    enrollment time by TimelineService.generate_for_enrollment().
    """
    try:
        from django.utils import timezone
        from apps.campaign_timeline.models import CampaignExecutionTimeline

        now = timezone.now()
        due_ids = list(
            CampaignExecutionTimeline.objects
            .filter(
                status=CampaignExecutionTimeline.STATUS_PENDING,
                scheduled_at__lte=now,
            )
            .values_list('id', flat=True)
            .order_by('scheduled_at')[:500]  # cap per-run to avoid memory spikes
        )
        for entry_id in due_ids:
            execute_timeline_step.delay(entry_id)
        if due_ids:
            logger.info(
                "poll_due_timeline_entries: dispatched %d entries", len(due_ids),
            )
    except Exception as exc:
        logger.exception("poll_due_timeline_entries error")
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=30, queue='campaigns',
          name='apps.campaign_timeline.tasks.cancel_enrollment_timeline')
def cancel_enrollment_timeline(self, enrollment_id: int, reason: str = 'enrollment_stopped') -> None:
    """
    Cancel all pending timeline entries for an enrollment.
    Called when an enrollment is stopped (reply, opt-out, manual).
    BRU-16: idempotent — already-cancelled entries are filtered out.
    """
    try:
        from apps.campaigns.models import CampaignEnrollment
        from apps.campaign_timeline.services import TimelineService

        try:
            enrollment = CampaignEnrollment.objects.get(pk=enrollment_id)
        except CampaignEnrollment.DoesNotExist:
            logger.warning(
                "cancel_enrollment_timeline: enrollment %d not found", enrollment_id,
            )
            return
        count = TimelineService.cancel_for_enrollment(enrollment=enrollment, reason=reason)
        logger.info(
            "cancel_enrollment_timeline: cancelled %d entries for enrollment %d",
            count, enrollment_id,
        )
    except Exception as exc:
        logger.exception(
            "cancel_enrollment_timeline error for enrollment %d", enrollment_id,
        )
        raise self.retry(exc=exc)
