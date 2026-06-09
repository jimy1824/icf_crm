import logging
from django.db import transaction
from django.utils import timezone

from apps.campaigns.models import Campaign, CampaignStep, CampaignEnrollment
from apps.audit.services import AuditService
from apps.common.events import event_bus

logger = logging.getLogger(__name__)

# BRU-09: quiet hours window (server-local time) — D-01 unresolved for exact definition
QUIET_HOUR_START = 21  # 9 PM
QUIET_HOUR_END = 8     # 8 AM


class CampaignService:

    @staticmethod
    @transaction.atomic
    def create_campaign(*, tenant, actor, name, steps_data=None) -> Campaign:
        campaign = Campaign.objects.create(
            tenant=tenant,
            name=name,
            created_by=actor,
            status=Campaign.STATUS_DRAFT,
        )
        if steps_data:
            for i, step in enumerate(steps_data, start=1):
                CampaignStep.objects.create(
                    campaign=campaign,
                    step_number=i,
                    channel=step['channel'],
                    subject=step.get('subject', ''),
                    content_template=step['content_template'],
                    delay_days=step.get('delay_days', 0),
                )
        AuditService.log(
            tenant=tenant, actor=actor,
            action='campaign.created',
            entity_type='Campaign', entity_id=campaign.pk,
            after_state={'name': name, 'step_count': len(steps_data or [])},
        )
        return campaign

    @staticmethod
    @transaction.atomic
    def activate_campaign(*, campaign, actor) -> Campaign:
        if campaign.status not in (Campaign.STATUS_DRAFT, Campaign.STATUS_PAUSED):
            from django.core.exceptions import ValidationError
            raise ValidationError(f"Cannot activate a campaign with status '{campaign.status}'.")
        step_count = campaign.steps.count()
        if step_count == 0:
            from django.core.exceptions import ValidationError
            raise ValidationError("Cannot activate a campaign with no steps.")
        campaign.status = Campaign.STATUS_ACTIVE
        campaign.save(update_fields=['status', 'updated_at'])
        AuditService.log(
            tenant=campaign.tenant, actor=actor,
            action='campaign.activated', entity_type='Campaign', entity_id=campaign.pk,
        )
        return campaign

    @staticmethod
    @transaction.atomic
    def pause_campaign(*, campaign, actor) -> Campaign:
        if campaign.status != Campaign.STATUS_ACTIVE:
            from django.core.exceptions import ValidationError
            raise ValidationError(f"Cannot pause a campaign with status '{campaign.status}'.")
        campaign.status = Campaign.STATUS_PAUSED
        campaign.save(update_fields=['status', 'updated_at'])
        AuditService.log(
            tenant=campaign.tenant, actor=actor,
            action='campaign.paused', entity_type='Campaign', entity_id=campaign.pk,
        )
        return campaign

    @staticmethod
    @transaction.atomic
    def enroll_subject(*, campaign, actor, lead) -> CampaignEnrollment:
        """
        BRU-07: check opt-out before enrolling.
        BRU-03: one active enrollment per lead per campaign.
        Every person in the funnel is a Lead regardless of their status (Lead/Prospect/Client/…).
        """
        from django.core.exceptions import ValidationError
        if campaign.status != Campaign.STATUS_ACTIVE:
            raise ValidationError("Can only enroll into an active campaign.")

        if lead is None:
            raise ValidationError("A Lead is required for enrollment.")

        # BRU-07: respect opt-out
        if lead.opted_out:
            raise ValidationError("BRU-07: Lead has opted out — cannot enroll.")
        if lead.is_suppressed:
            raise ValidationError("BRU-19: Lead is suppressed — cannot enroll.")

        # BRU-03: prevent duplicate active enrollment
        if CampaignEnrollment.objects.filter(
            campaign=campaign, lead=lead, status=CampaignEnrollment.STATUS_ACTIVE,
        ).exists():
            raise ValidationError("BRU-03: Subject already has an active enrollment in this campaign.")

        enrollment = CampaignEnrollment.objects.create(
            tenant=campaign.tenant,
            campaign=campaign,
            lead=lead,
            status=CampaignEnrollment.STATUS_ACTIVE,
            current_step=0,
        )
        AuditService.log(
            tenant=campaign.tenant, actor=actor,
            action='campaign.enrolled',
            entity_type='CampaignEnrollment', entity_id=enrollment.pk,
            after_state={'campaign': campaign.pk, 'lead': lead.pk},
        )
        # Generate pre-computed execution timeline (all steps scheduled at once)
        from apps.campaign_timeline.services import TimelineService
        from apps.campaign_timeline.tasks import poll_due_timeline_entries  # noqa: trigger registration
        TimelineService.generate_for_enrollment(enrollment)
        return enrollment

    @staticmethod
    @transaction.atomic
    def stop_enrollment(*, enrollment, actor, reason) -> CampaignEnrollment:
        """BRU-21: stop a single enrollment."""
        if enrollment.status != CampaignEnrollment.STATUS_ACTIVE:
            from django.core.exceptions import ValidationError
            raise ValidationError("Enrollment is not active.")
        enrollment.status = CampaignEnrollment.STATUS_STOPPED
        enrollment.stopped_reason = reason
        enrollment.save(update_fields=['status', 'stopped_reason', 'updated_at'])
        AuditService.log(
            tenant=enrollment.tenant, actor=actor,
            action='campaign.enrollment_stopped',
            entity_type='CampaignEnrollment', entity_id=enrollment.pk,
            after_state={'reason': reason},
        )
        # Cancel pending timeline entries asynchronously
        from apps.campaign_timeline.tasks import cancel_enrollment_timeline
        cancel_enrollment_timeline.delay(enrollment.pk, reason)
        return enrollment

    @staticmethod
    def stop_all_enrollments_for_subject(*, tenant, lead, reason) -> int:
        """
        BRU-21: stop all active enrollments for a lead (called on reply/opt-out).
        BRU-03: stop-on-reply ends the campaign sequence.
        Every person in the funnel is a Lead — no client FK needed.
        """
        if lead is None:
            return 0
        stopped_ids = list(
            CampaignEnrollment.objects.filter(
                tenant=tenant, lead=lead, status=CampaignEnrollment.STATUS_ACTIVE,
            ).values_list('id', flat=True)
        )
        if not stopped_ids:
            return 0
        count = CampaignEnrollment.objects.filter(pk__in=stopped_ids).update(
            status=CampaignEnrollment.STATUS_STOPPED, stopped_reason=reason,
        )
        logger.info("Stopped %d enrollments for lead=%s (reason=%s)", count, lead.pk, reason)
        # Cancel pending timeline entries for each stopped enrollment
        from apps.campaign_timeline.tasks import cancel_enrollment_timeline
        for eid in stopped_ids:
            cancel_enrollment_timeline.delay(eid, reason)
        return count
