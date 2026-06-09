"""
Compliance services.
BRU-37: RetentionService  — enforce retention windows, block premature deletion.
BRU-38: LegalHoldService  — place/lift holds that override all deletion.
BRU-36: SupervisionService — review queue, approve/reject advisor communications.
"""
import logging
from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone

from apps.audit.services import AuditService
from apps.common.events import event_bus
from apps.compliance.models import (
    RetentionPolicy,
    RetentionRecord,
    SupervisionReview,
    SupervisionRule,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# BRU-37: Retention enforcement
# ---------------------------------------------------------------------------

class RetentionService:

    @staticmethod
    @transaction.atomic
    def register(
        *, tenant, entity_type: str, entity_id, actor=None,
        retention_years: int | None = None,
    ) -> RetentionRecord:
        """
        Create a RetentionRecord for a newly created entity.
        Retention years come from the tenant's RetentionPolicy for that entity_type;
        falls back to the supplied retention_years, then defaults to 7.
        BRU-37: retained_until can never be shortened after creation.
        """
        years = retention_years
        if years is None:
            policy = RetentionPolicy.objects.filter(
                tenant=tenant, entity_type=entity_type.lower(),
            ).first()
            years = policy.retention_years if policy else 7

        retained_until = date.today() + timedelta(days=years * 365)
        record, created = RetentionRecord.objects.get_or_create(
            tenant=tenant,
            entity_type=entity_type,
            entity_id=str(entity_id),
            defaults={'retained_until': retained_until},
        )
        if not created:
            # BRU-37: only extend, never shorten
            if retained_until > record.retained_until:
                record.retained_until = retained_until
                record.save(update_fields=['retained_until', 'updated_at'])
        return record

    @staticmethod
    def is_deletable(*, tenant, entity_type: str, entity_id) -> bool:
        """
        BRU-37/38: returns True only if retention window has expired AND no legal hold.
        """
        try:
            record = RetentionRecord.objects.get(
                tenant=tenant,
                entity_type=entity_type,
                entity_id=str(entity_id),
            )
        except RetentionRecord.DoesNotExist:
            return True  # no retention record → not under retention management

        # BRU-38: legal hold blocks deletion absolutely
        if record.is_under_legal_hold:
            return False

        return date.today() > record.retained_until

    @staticmethod
    def assert_deletable(*, tenant, entity_type: str, entity_id) -> None:
        """Raise ValidationError if the entity is not yet deletable."""
        if not RetentionService.is_deletable(
            tenant=tenant, entity_type=entity_type, entity_id=entity_id,
        ):
            raise ValidationError(
                f"BRU-37/38: {entity_type} {entity_id} is under an active retention "
                "window or legal hold and cannot be deleted."
            )

    @staticmethod
    @transaction.atomic
    def approve_deletion(
        *, tenant, entity_type: str, entity_id, actor,
    ) -> RetentionRecord:
        """
        Defensible deletion: compliance officer confirms the record is past retention
        and not held, then marks it cleared_for_deletion.
        BRU-38: raises if a legal hold is active.
        """
        RetentionService.assert_deletable(
            tenant=tenant, entity_type=entity_type, entity_id=entity_id,
        )
        record = RetentionRecord.objects.get(
            tenant=tenant, entity_type=entity_type, entity_id=str(entity_id),
        )
        record.cleared_for_deletion_at = date.today()
        record.deletion_approved_by = actor
        record.save(update_fields=['cleared_for_deletion_at', 'deletion_approved_by', 'updated_at'])
        AuditService.log(
            tenant=tenant, actor=actor,
            action='retention.deletion_approved',
            entity_type=entity_type, entity_id=entity_id,
            after_state={'cleared_for_deletion_at': str(record.cleared_for_deletion_at)},
        )
        return record

    @staticmethod
    def configure_policy(
        *, tenant, entity_type: str, retention_years: int, actor,
    ) -> RetentionPolicy:
        """Set or update the tenant's retention policy for an entity type."""
        policy, _ = RetentionPolicy.objects.update_or_create(
            tenant=tenant,
            entity_type=entity_type,
            defaults={'retention_years': retention_years},
        )
        AuditService.log(
            tenant=tenant, actor=actor,
            action='retention.policy_configured',
            entity_type='RetentionPolicy', entity_id=policy.pk,
            after_state={'entity_type': entity_type, 'retention_years': retention_years},
        )
        return policy


# ---------------------------------------------------------------------------
# BRU-38: Legal hold
# ---------------------------------------------------------------------------

class LegalHoldService:

    @staticmethod
    @transaction.atomic
    def place_hold(
        *, tenant, entity_type: str, entity_id, actor, reason: str,
    ) -> RetentionRecord:
        """
        BRU-38: places a legal hold that blocks deletion regardless of retention window.
        Creates a RetentionRecord first if one does not yet exist.
        """
        record = RetentionService.register(
            tenant=tenant, entity_type=entity_type, entity_id=entity_id, actor=actor,
        )
        record.is_under_legal_hold = True
        record.hold_placed_by = actor
        record.hold_placed_at = timezone.now()
        record.hold_reason = reason
        record.save(update_fields=[
            'is_under_legal_hold', 'hold_placed_by', 'hold_placed_at',
            'hold_reason', 'updated_at',
        ])
        AuditService.log(
            tenant=tenant, actor=actor,
            action='legal_hold.placed',
            entity_type=entity_type, entity_id=entity_id,
            after_state={'reason': reason},
        )
        event_bus.emit(
            'compliance.legal_hold_placed',
            tenant_id=tenant.pk,
            entity_type=entity_type,
            entity_id=str(entity_id),
        )
        return record

    @staticmethod
    @transaction.atomic
    def lift_hold(
        *, tenant, entity_type: str, entity_id, actor, reason: str = '',
    ) -> RetentionRecord:
        """
        BRU-38: lifts a legal hold. Only authorised compliance officers should call this.
        Deletion remains blocked until the retention window also expires.
        """
        try:
            record = RetentionRecord.objects.get(
                tenant=tenant, entity_type=entity_type, entity_id=str(entity_id),
            )
        except RetentionRecord.DoesNotExist:
            raise ValidationError(
                f"No retention record for {entity_type}/{entity_id}."
            )
        record.is_under_legal_hold = False
        record.save(update_fields=['is_under_legal_hold', 'updated_at'])
        AuditService.log(
            tenant=tenant, actor=actor,
            action='legal_hold.lifted',
            entity_type=entity_type, entity_id=entity_id,
            after_state={'reason': reason},
        )
        return record


# ---------------------------------------------------------------------------
# BRU-36: Supervision / review workflow
# ---------------------------------------------------------------------------

class SupervisionService:

    @staticmethod
    def get_applicable_rule(
        *, tenant, advisor, channel: str,
    ) -> SupervisionRule | None:
        """
        Return the first active rule that applies to this advisor+channel.
        Advisor-specific rules take priority over tenant-wide (null advisor) rules.
        """
        qs = SupervisionRule.objects.filter(
            tenant=tenant, is_active=True,
        ).filter(
            models.Q(applies_to_advisor=advisor) | models.Q(applies_to_advisor__isnull=True),
        ).filter(
            models.Q(channel=channel) | models.Q(channel='all'),
        ).order_by(
            models.Case(
                models.When(applies_to_advisor=advisor, then=0),
                default=1,
                output_field=models.IntegerField(),
            ),
            'id',
        )
        return qs.first()

    @staticmethod
    @transaction.atomic
    def flag_for_review(
        *, tenant, communication, advisor, actor=None,
    ) -> SupervisionReview | None:
        """
        BRU-36: called after a Communication is recorded.
        Creates a SupervisionReview if a rule applies; returns None otherwise.
        """
        rule = SupervisionService.get_applicable_rule(
            tenant=tenant, advisor=advisor, channel=communication.channel,
        )
        if not rule:
            return None

        review, created = SupervisionReview.objects.get_or_create(
            tenant=tenant,
            communication=communication,
            defaults={
                'rule': rule,
                'supervisor': rule.supervisor,
                'status': SupervisionReview.STATUS_PENDING,
            },
        )
        if created:
            AuditService.log(
                tenant=tenant, actor=actor or advisor,
                action='supervision.review_created',
                entity_type='SupervisionReview', entity_id=review.pk,
                after_state={
                    'communication_id': communication.pk,
                    'rule': rule.pk,
                    'mode': rule.review_mode,
                },
            )
            event_bus.emit(
                'compliance.review_queued',
                tenant_id=tenant.pk,
                review_id=review.pk,
                supervisor_id=rule.supervisor_id,
                review_mode=rule.review_mode,
            )
        return review

    @staticmethod
    @transaction.atomic
    def approve(
        *, review: SupervisionReview, reviewer, notes: str = '',
    ) -> SupervisionReview:
        """BRU-36: supervisor approves the communication."""
        if review.status != SupervisionReview.STATUS_PENDING:
            raise ValidationError(
                f"Review {review.pk} is already '{review.status}' — cannot approve."
            )
        review.status = SupervisionReview.STATUS_APPROVED
        review.review_notes = notes
        review.reviewed_at = timezone.now()
        review.reviewed_by = reviewer
        review.save(update_fields=[
            'status', 'review_notes', 'reviewed_at', 'reviewed_by', 'updated_at',
        ])
        AuditService.log(
            tenant=review.tenant, actor=reviewer,
            action='supervision.approved',
            entity_type='SupervisionReview', entity_id=review.pk,
            before_state={'status': 'pending'},
            after_state={'status': 'approved', 'notes': notes},
        )
        event_bus.emit(
            'compliance.review_approved',
            tenant_id=review.tenant_id,
            review_id=review.pk,
            communication_id=review.communication_id,
        )
        return review

    @staticmethod
    @transaction.atomic
    def reject(
        *, review: SupervisionReview, reviewer, notes: str,
    ) -> SupervisionReview:
        """BRU-36: supervisor rejects; triggers notification to advisor."""
        if review.status != SupervisionReview.STATUS_PENDING:
            raise ValidationError(
                f"Review {review.pk} is already '{review.status}' — cannot reject."
            )
        review.status = SupervisionReview.STATUS_REJECTED
        review.review_notes = notes
        review.reviewed_at = timezone.now()
        review.reviewed_by = reviewer
        review.save(update_fields=[
            'status', 'review_notes', 'reviewed_at', 'reviewed_by', 'updated_at',
        ])
        AuditService.log(
            tenant=review.tenant, actor=reviewer,
            action='supervision.rejected',
            entity_type='SupervisionReview', entity_id=review.pk,
            before_state={'status': 'pending'},
            after_state={'status': 'rejected', 'notes': notes},
        )
        event_bus.emit(
            'compliance.review_rejected',
            tenant_id=review.tenant_id,
            review_id=review.pk,
            communication_id=review.communication_id,
        )
        return review

    @staticmethod
    @transaction.atomic
    def escalate(
        *, review: SupervisionReview, reviewer, notes: str = '',
    ) -> SupervisionReview:
        """BRU-36: escalate to senior compliance officer."""
        if review.status not in (
            SupervisionReview.STATUS_PENDING, SupervisionReview.STATUS_APPROVED,
        ):
            raise ValidationError(
                f"Review {review.pk} cannot be escalated from status '{review.status}'."
            )
        review.status = SupervisionReview.STATUS_ESCALATED
        review.review_notes = notes
        review.reviewed_by = reviewer
        review.reviewed_at = timezone.now()
        review.save(update_fields=[
            'status', 'review_notes', 'reviewed_at', 'reviewed_by', 'updated_at',
        ])
        AuditService.log(
            tenant=review.tenant, actor=reviewer,
            action='supervision.escalated',
            entity_type='SupervisionReview', entity_id=review.pk,
            after_state={'status': 'escalated'},
        )
        return review

    @staticmethod
    def is_held_pending_review(*, communication) -> bool:
        """
        BRU-36: pre-send mode — True if the communication has an outstanding
        pre-send review that must be approved before dispatch.
        """
        try:
            review = SupervisionReview.objects.select_related('rule').get(
                communication=communication,
            )
        except SupervisionReview.DoesNotExist:
            return False
        if review.rule and review.rule.review_mode == SupervisionRule.REVIEW_MODE_PRE:
            return review.status == SupervisionReview.STATUS_PENDING
        return False
