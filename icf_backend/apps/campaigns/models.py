from django.conf import settings
from django.db import models
from apps.common.models import BaseModel, TenantBaseModel


class Campaign(TenantBaseModel):
    STATUS_DRAFT = 'draft'
    STATUS_ACTIVE = 'active'
    STATUS_PAUSED = 'paused'
    STATUS_COMPLETED = 'completed'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_PAUSED, 'Paused'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    territories = models.ManyToManyField(
        'territories.Territory',
        blank=True,
        related_name='campaigns',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='created_campaigns',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'], name='unique_campaign_name_per_tenant'
            )
        ]
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class CampaignStep(BaseModel):
    CHANNEL_EMAIL = 'email'
    CHANNEL_SMS = 'sms'
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, 'Email'),
        (CHANNEL_SMS, 'SMS'),
    ]

    DELAY_UNIT_HOURS = 'hours'
    DELAY_UNIT_DAYS = 'days'
    DELAY_UNIT_WEEKS = 'weeks'
    DELAY_UNIT_CHOICES = [
        (DELAY_UNIT_HOURS, 'Hours'),
        (DELAY_UNIT_DAYS, 'Days'),
        (DELAY_UNIT_WEEKS, 'Weeks'),
    ]

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='steps')
    step_number = models.PositiveIntegerField()
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    subject = models.CharField(max_length=500, blank=True)      # email only
    content_template = models.TextField()
    delay_days = models.PositiveIntegerField(default=0)          # BRU-09: kept for legacy compat
    delay_value = models.PositiveIntegerField(default=0)         # actual numeric delay
    delay_unit = models.CharField(
        max_length=10, choices=DELAY_UNIT_CHOICES, default=DELAY_UNIT_DAYS,
    )  # hours / days / weeks

    class Meta:
        unique_together = [('campaign', 'step_number')]
        ordering = ['step_number']

    def __str__(self):
        return f"Step {self.step_number} ({self.channel}) — {self.campaign.name}"


class CampaignEnrollment(TenantBaseModel):
    STATUS_ACTIVE = 'active'
    STATUS_STOPPED = 'stopped'
    STATUS_COMPLETED = 'completed'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_STOPPED, 'Stopped'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    REASON_RESPONSE = 'response'
    REASON_OPT_OUT = 'opt_out'
    REASON_MANUAL = 'manual'
    REASON_COMPLETED = 'completed'
    REASON_CHOICES = [
        (REASON_RESPONSE, 'Response'),
        (REASON_OPT_OUT, 'Opt Out'),
        (REASON_MANUAL, 'Manual'),
        (REASON_COMPLETED, 'Completed'),
        ('', 'N/A'),
    ]

    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name='enrollments')
    lead = models.ForeignKey(
        'leads.Lead', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='campaign_enrollments',
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    current_step = models.PositiveIntegerField(default=0)
    stopped_reason = models.CharField(max_length=20, choices=REASON_CHOICES, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(lead__isnull=False),
                name='enrollment_requires_lead',
            )
        ]
        indexes = [
            models.Index(fields=['tenant', 'status']),
        ]

    def __str__(self):
        return f"{self.lead} in {self.campaign.name} ({self.status})"
