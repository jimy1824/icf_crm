"""
Compliance models for BRU-36, BRU-37, BRU-38.
M-A: Books-and-Records / Retention (BRU-37)
M-B: Supervision / Review workflow (BRU-36)
M-C: Legal holds overriding deletion (BRU-38)
"""
from django.conf import settings
from django.db import models

from apps.common.models import BaseModel, TenantBaseModel


# ---------------------------------------------------------------------------
# Retention (BRU-37, M-A, M-C)
# ---------------------------------------------------------------------------

class RetentionPolicy(TenantBaseModel):
    """
    BRU-37: per-tenant, per-entity-type configurable retention schedule.
    D-07: actual periods depend on regulatory regime (SEC/FINRA/state RIA).
    Default: 7 years for communications, 5 years for financials.
    """
    ENTITY_COMMUNICATION = 'communication'
    ENTITY_FINANCIAL = 'financial'
    ENTITY_DOCUMENT = 'document'
    ENTITY_AUDIT = 'audit'
    ENTITY_CHOICES = [
        (ENTITY_COMMUNICATION, 'Communication'),
        (ENTITY_FINANCIAL, 'Financial Record'),
        (ENTITY_DOCUMENT, 'Document'),
        (ENTITY_AUDIT, 'Audit Event'),
    ]

    entity_type = models.CharField(max_length=50, choices=ENTITY_CHOICES)
    # Minimum retention in years — immutable during any active hold
    retention_years = models.PositiveSmallIntegerField(default=7)
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = [('tenant', 'entity_type')]
        ordering = ['entity_type']

    def __str__(self):
        return f"{self.tenant} — {self.entity_type} ({self.retention_years}yr)"


class RetentionRecord(TenantBaseModel):
    """
    BRU-37/38: tracks the retention window and legal-hold state for a single
    entity instance. One row per (entity_type, entity_id).

    Immutability rule: retained_until cannot be shortened once set.
    Legal hold: is_under_legal_hold=True blocks all deletion regardless of window.
    """
    entity_type = models.CharField(max_length=100)   # e.g. 'Communication', 'AuditEvent'
    entity_id = models.CharField(max_length=36)       # pk of the protected record

    retained_until = models.DateField()               # BRU-37: must not be shortened
    is_under_legal_hold = models.BooleanField(default=False)  # BRU-38

    # Who placed the hold and why
    hold_placed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='placed_holds',
    )
    hold_placed_at = models.DateTimeField(null=True, blank=True)
    hold_reason = models.TextField(blank=True)

    # Defensible deletion: set when the record is cleared for purge
    cleared_for_deletion_at = models.DateField(null=True, blank=True)
    deletion_approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_deletions',
    )

    class Meta:
        unique_together = [('tenant', 'entity_type', 'entity_id')]
        indexes = [
            models.Index(fields=['tenant', 'entity_type', 'retained_until']),
            models.Index(fields=['tenant', 'is_under_legal_hold']),
        ]

    def __str__(self):
        hold = ' [HELD]' if self.is_under_legal_hold else ''
        return f"{self.entity_type}/{self.entity_id} until {self.retained_until}{hold}"


# ---------------------------------------------------------------------------
# Supervision / review workflow (BRU-36, M-B)
# ---------------------------------------------------------------------------

class SupervisionRule(TenantBaseModel):
    """
    BRU-36: per-tenant rule defining which advisor communications require
    supervisor review before or after sending.
    """
    REVIEW_MODE_PRE = 'pre_send'     # hold outbound until approved
    REVIEW_MODE_POST = 'post_send'   # send immediately, flag for review
    REVIEW_MODE_CHOICES = [
        (REVIEW_MODE_PRE, 'Pre-Send Review'),
        (REVIEW_MODE_POST, 'Post-Send Review'),
    ]

    # Which advisors this rule applies to (null = all advisors in tenant)
    applies_to_advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='supervision_rules',
    )
    channel = models.CharField(
        max_length=10,
        choices=[('email', 'Email'), ('sms', 'SMS'), ('all', 'All')],
        default='all',
    )
    review_mode = models.CharField(
        max_length=20, choices=REVIEW_MODE_CHOICES, default=REVIEW_MODE_POST,
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='supervised_rules',
    )
    description = models.CharField(max_length=500, blank=True)

    class Meta:
        indexes = [models.Index(fields=['tenant', 'is_active'])]

    def __str__(self):
        target = self.applies_to_advisor or 'all advisors'
        return f"{self.tenant} — supervise {target} ({self.channel}, {self.review_mode})"


class SupervisionReview(TenantBaseModel):
    """
    BRU-36: one review record per communication under supervision.
    Pre-send: status starts PENDING — send is held until APPROVED.
    Post-send: status starts PENDING — supervisor reviews after delivery.
    """
    STATUS_PENDING = 'pending'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'
    STATUS_ESCALATED = 'escalated'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending Review'),
        (STATUS_APPROVED, 'Approved'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_ESCALATED, 'Escalated'),
    ]

    communication = models.OneToOneField(
        'communications.Communication',
        on_delete=models.CASCADE,
        related_name='supervision_review',
    )
    rule = models.ForeignKey(
        SupervisionRule, on_delete=models.SET_NULL, null=True,
        related_name='reviews',
    )
    supervisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='supervision_reviews',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    review_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='completed_reviews',
    )

    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['supervisor', 'status']),
        ]

    def __str__(self):
        return f"Review of comm {self.communication_id} — {self.status}"
