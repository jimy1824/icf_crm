from django.db import models

from apps.common.models import TenantBaseModel


class CampaignExecutionTimeline(TenantBaseModel):
    """
    Pre-generated execution schedule for one campaign step against one lead.

    Generated atomically at enrollment time — all future steps are written
    immediately with their computed scheduled_at datetimes.  Celery workers
    query status=Pending + scheduled_at<=now() and execute without
    recalculating intervals.

    BRU-01: tenant-scoped via TenantBaseModel.
    BRU-09: scheduled_at has already been shifted to office hours by the
            timeline generation service — workers never re-apply that logic.
    BRU-16: execute_timeline_step is idempotent — safe to retry.
    """

    STATUS_PENDING = 'pending'
    STATUS_SCHEDULED = 'scheduled'
    STATUS_EXECUTED = 'executed'
    STATUS_FAILED = 'failed'
    STATUS_CANCELLED = 'cancelled'
    STATUS_SKIPPED = 'skipped'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SCHEDULED, 'Scheduled'),
        (STATUS_EXECUTED, 'Executed'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_SKIPPED, 'Skipped'),
    ]

    enrollment = models.ForeignKey(
        'campaigns.CampaignEnrollment',
        on_delete=models.CASCADE,
        related_name='timeline_entries',
    )
    campaign = models.ForeignKey(
        'campaigns.Campaign',
        on_delete=models.CASCADE,
        related_name='timeline_entries',
    )
    lead = models.ForeignKey(
        'leads.Lead',
        on_delete=models.CASCADE,
        related_name='campaign_timeline_entries',
    )
    campaign_step = models.ForeignKey(
        'campaigns.CampaignStep',
        on_delete=models.CASCADE,
        related_name='timeline_entries',
    )

    step_order = models.PositiveIntegerField()
    step_type = models.CharField(max_length=10)           # 'email' | 'sms'

    # Content snapshot at enrollment time — immutable after creation
    subject_snapshot = models.CharField(max_length=500, blank=True)
    body_snapshot = models.TextField()

    scheduled_at = models.DateTimeField(
        help_text='UTC datetime, pre-shifted to office hours.',
        db_index=True,
    )
    executed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=STATUS_PENDING,
    )
    failure_reason = models.TextField(blank=True)

    # Track if this entry was shifted from original computed time (for analytics)
    was_office_hour_shifted = models.BooleanField(default=False)
    original_scheduled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['enrollment', 'step_order']
        indexes = [
            models.Index(fields=['tenant', 'status', 'scheduled_at']),
            models.Index(fields=['enrollment', 'step_order']),
            models.Index(fields=['lead', 'status']),
            models.Index(fields=['campaign', 'status', 'scheduled_at']),
            models.Index(fields=['tenant', 'scheduled_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['enrollment', 'campaign_step'],
                name='unique_timeline_entry_per_enrollment_step',
            )
        ]

    def __str__(self):
        return (
            f"Timeline[{self.pk}] lead={self.lead_id} "
            f"step={self.step_order} status={self.status} "
            f"@{self.scheduled_at}"
        )
