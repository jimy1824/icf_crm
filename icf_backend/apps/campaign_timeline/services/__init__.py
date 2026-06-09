"""
Campaign Execution Timeline services.

Core contract
─────────────
TimelineService.generate_for_enrollment(enrollment)
    Called once at enrollment time.  Computes ALL future scheduled_at
    datetimes immediately and stores them in CampaignExecutionTimeline.
    Workers never recalculate intervals.

TimelineService.cancel_for_enrollment(enrollment)
    Cancels all Pending/Scheduled entries when an enrollment is stopped.

TimelineService.execute_entry(entry_id)
    Idempotent execution of one timeline entry (called by the Celery worker).
"""
import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone as dj_tz

logger = logging.getLogger(__name__)


def _compute_delay(step, anchor_dt):
    """Return the raw (pre-office-hour) scheduled datetime for a step relative to anchor_dt."""
    from apps.campaigns.models import CampaignStep
    unit = step.delay_unit
    value = step.delay_value
    if unit == CampaignStep.DELAY_UNIT_HOURS:
        return anchor_dt + timedelta(hours=value)
    elif unit == CampaignStep.DELAY_UNIT_WEEKS:
        return anchor_dt + timedelta(weeks=value)
    else:  # days (default, also covers legacy delay_days)
        effective = value if value else step.delay_days
        return anchor_dt + timedelta(days=effective)


class TimelineService:

    @staticmethod
    @transaction.atomic
    def generate_for_enrollment(enrollment) -> list:
        """
        Generate one CampaignExecutionTimeline row per step for the given enrollment.
        Steps are scheduled relative to enrollment time, each step anchored to
        the previous step's scheduled_at.

        Returns the list of created timeline entries.
        BRU-09: each computed time is shifted to office hours via TimezoneService.
        """
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        from apps.timezones.services import TimezoneService

        tenant = enrollment.tenant
        campaign = enrollment.campaign
        lead = enrollment.lead

        steps = list(campaign.steps.all().order_by('step_number'))
        if not steps:
            return []

        now = dj_tz.now()
        anchor = now  # first step uses now as anchor
        entries = []

        for step in steps:
            raw_dt = _compute_delay(step, anchor)
            shifted_dt = TimezoneService.shift_to_office_hours(raw_dt, tenant)
            was_shifted = shifted_dt != raw_dt

            entry = CampaignExecutionTimeline(
                tenant=tenant,
                enrollment=enrollment,
                campaign=campaign,
                lead=lead,
                campaign_step=step,
                step_order=step.step_number,
                step_type=step.channel,
                subject_snapshot=step.subject,
                body_snapshot=step.content_template,
                scheduled_at=shifted_dt,
                status=CampaignExecutionTimeline.STATUS_PENDING,
                was_office_hour_shifted=was_shifted,
                original_scheduled_at=raw_dt if was_shifted else None,
            )
            entries.append(entry)
            anchor = shifted_dt  # each subsequent step is relative to previous

        CampaignExecutionTimeline.objects.bulk_create(entries)
        logger.info(
            "TimelineService: generated %d entries for enrollment=%d",
            len(entries), enrollment.pk,
        )
        return entries

    @staticmethod
    @transaction.atomic
    def cancel_for_enrollment(enrollment, reason: str = 'enrollment_stopped') -> int:
        """
        Cancel all Pending/Scheduled timeline entries for the enrollment.
        Called when an enrollment is stopped (reply, opt-out, manual).
        """
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        count = CampaignExecutionTimeline.objects.filter(
            tenant=enrollment.tenant,
            enrollment=enrollment,
            status__in=[
                CampaignExecutionTimeline.STATUS_PENDING,
                CampaignExecutionTimeline.STATUS_SCHEDULED,
            ],
        ).update(
            status=CampaignExecutionTimeline.STATUS_CANCELLED,
            failure_reason=reason,
        )
        logger.info(
            "TimelineService: cancelled %d entries for enrollment=%d",
            count, enrollment.pk,
        )
        return count

    @staticmethod
    @transaction.atomic
    def execute_entry(entry_id: int) -> bool:
        """
        Execute one timeline entry idempotently.
        BRU-16: safe to call twice — second call is a no-op.
        Returns True if executed, False if skipped/already done.
        """
        from django.db.models import Q
        from apps.campaign_timeline.models import CampaignExecutionTimeline
        from apps.campaigns.models import CampaignEnrollment
        from apps.communications.services import CommunicationService
        from apps.common.edge_cases import assert_mailbox_active
        from django.core.exceptions import ValidationError as DjValidationError

        try:
            entry = (
                CampaignExecutionTimeline.objects
                .select_for_update()
                .select_related('enrollment', 'campaign', 'lead', 'campaign_step', 'tenant')
                .get(pk=entry_id)
            )
        except CampaignExecutionTimeline.DoesNotExist:
            logger.warning("execute_entry: entry %d not found", entry_id)
            return False

        # BRU-16: idempotency guard
        if entry.status not in (
            CampaignExecutionTimeline.STATUS_PENDING,
            CampaignExecutionTimeline.STATUS_SCHEDULED,
        ):
            logger.info(
                "execute_entry: entry %d already %s — skipping", entry_id, entry.status,
            )
            return False

        enrollment = entry.enrollment
        lead = entry.lead
        tenant = entry.tenant

        # BRU-03: stop if enrollment is no longer active
        if enrollment.status != CampaignEnrollment.STATUS_ACTIVE:
            entry.status = CampaignExecutionTimeline.STATUS_CANCELLED
            entry.failure_reason = f'enrollment_{enrollment.status}'
            entry.save(update_fields=['status', 'failure_reason', 'updated_at'])
            return False

        # BRU-07: opt-out check
        if lead.opted_out or lead.is_suppressed:
            entry.status = CampaignExecutionTimeline.STATUS_SKIPPED
            entry.failure_reason = 'opted_out'
            entry.save(update_fields=['status', 'failure_reason', 'updated_at'])
            return False

        step = entry.campaign_step

        # E-1 (BRU-05): check mailbox before email steps
        if step.channel == 'email':
            from apps.communications.models import MailboxConnection
            advisor = enrollment.campaign.created_by
            if advisor:
                conn = MailboxConnection.objects.filter(
                    advisor=advisor, tenant=tenant,
                    status=MailboxConnection.STATUS_ACTIVE,
                ).first()
                if conn:
                    try:
                        assert_mailbox_active(conn)
                    except DjValidationError:
                        from apps.communications.services import MailboxService
                        MailboxService.suspend_on_token_expiry(connection=conn)
                        entry.status = CampaignExecutionTimeline.STATUS_FAILED
                        entry.failure_reason = 'BRU-05: mailbox token expired'
                        entry.save(update_fields=['status', 'failure_reason', 'updated_at'])
                        # Re-queue via task for later retry
                        from apps.campaign_timeline.tasks import execute_timeline_step
                        execute_timeline_step.apply_async(args=[entry_id], countdown=3600)
                        return False

        # BRU-18/19: suppression check
        if step.channel == 'email' and lead.email:
            if CommunicationService.is_suppressed_email(tenant=tenant, email=lead.email):
                entry.status = CampaignExecutionTimeline.STATUS_SKIPPED
                entry.failure_reason = 'email_suppressed'
                entry.save(update_fields=['status', 'failure_reason', 'updated_at'])
                return False
        elif step.channel == 'sms' and lead.phone:
            if CommunicationService.is_suppressed_phone(tenant=tenant, phone=lead.phone):
                entry.status = CampaignExecutionTimeline.STATUS_SKIPPED
                entry.failure_reason = 'sms_suppressed'
                entry.save(update_fields=['status', 'failure_reason', 'updated_at'])
                return False

        # Record communication (BRU-16: external_id ensures dedup)
        external_id = f"timeline-{entry.pk}-enrollment-{enrollment.pk}"
        CommunicationService.record_communication(
            tenant=tenant,
            channel=step.channel,
            direction='outbound',
            body_ref=entry.body_snapshot[:500],
            external_id=external_id,
            lead=lead,
            subject=entry.subject_snapshot,
            campaign_enrollment=enrollment,
        )

        # Update enrollment step counter
        enrollment.current_step = entry.step_order
        enrollment.save(update_fields=['current_step', 'updated_at'])

        # Check if this was the last step
        remaining = CampaignExecutionTimeline.objects.filter(
            enrollment=enrollment,
            status=CampaignExecutionTimeline.STATUS_PENDING,
            step_order__gt=entry.step_order,
        ).exists()
        if not remaining:
            enrollment.status = CampaignEnrollment.STATUS_COMPLETED
            enrollment.stopped_reason = CampaignEnrollment.REASON_COMPLETED
            enrollment.save(update_fields=['status', 'stopped_reason', 'updated_at'])

        entry.status = CampaignExecutionTimeline.STATUS_EXECUTED
        entry.executed_at = dj_tz.now()
        entry.save(update_fields=['status', 'executed_at', 'updated_at'])

        return True


class TimelineAnalyticsService:

    @staticmethod
    def dashboard_summary(tenant) -> dict:
        """
        Return counts for the admin/advisor dashboard:
        scheduled today, executed today, failed today, outside-hours adjustments.
        """
        from django.utils import timezone as dj_tz
        from apps.campaign_timeline.models import CampaignExecutionTimeline

        now = dj_tz.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = now.replace(hour=23, minute=59, second=59, microsecond=999999)

        qs = CampaignExecutionTimeline.objects.filter(tenant=tenant)

        return {
            'pending_now': qs.filter(
                status=CampaignExecutionTimeline.STATUS_PENDING,
                scheduled_at__lte=now,
            ).count(),
            'scheduled_today': qs.filter(
                status__in=[
                    CampaignExecutionTimeline.STATUS_PENDING,
                    CampaignExecutionTimeline.STATUS_SCHEDULED,
                ],
                scheduled_at__range=(today_start, today_end),
            ).count(),
            'executed_today': qs.filter(
                status=CampaignExecutionTimeline.STATUS_EXECUTED,
                executed_at__range=(today_start, today_end),
            ).count(),
            'failed_today': qs.filter(
                status=CampaignExecutionTimeline.STATUS_FAILED,
                updated_at__range=(today_start, today_end),
            ).count(),
            'office_hour_shifts': qs.filter(
                was_office_hour_shifted=True,
                scheduled_at__range=(today_start, today_end),
            ).count(),
        }

    @staticmethod
    def upcoming_for_advisor(advisor, hours_ahead: int = 24) -> list:
        """Return pending timeline entries for the advisor's leads in the next N hours."""
        from django.utils import timezone as dj_tz
        from apps.campaign_timeline.models import CampaignExecutionTimeline

        now = dj_tz.now()
        cutoff = now + __import__('datetime').timedelta(hours=hours_ahead)

        return list(
            CampaignExecutionTimeline.objects
            .filter(
                tenant=advisor.tenant,
                lead__assigned_advisors=advisor,
                status=CampaignExecutionTimeline.STATUS_PENDING,
                scheduled_at__range=(now, cutoff),
            )
            .select_related('lead', 'campaign', 'campaign_step')
            .order_by('scheduled_at')
        )
