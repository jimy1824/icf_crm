from django.conf import settings
from django.db import models
from apps.common.models import BaseModel, TenantBaseModel


# ---------------------------------------------------------------------------
# Mailbox OAuth connections (FM-07)
# ---------------------------------------------------------------------------

class MailboxConnection(TenantBaseModel):
    """
    OAuth connection between an advisor's mailbox and the platform.
    BRU-05: token expiry suspends automation and alerts.
    """
    PROVIDER_GMAIL = 'gmail'
    PROVIDER_OUTLOOK = 'outlook'
    PROVIDER_CHOICES = [
        (PROVIDER_GMAIL, 'Gmail / Google Workspace'),
        (PROVIDER_OUTLOOK, 'Outlook / Microsoft 365'),
    ]

    STATUS_ACTIVE = 'active'
    STATUS_SUSPENDED = 'suspended'   # BRU-05: token expired/invalid
    STATUS_REVOKED = 'revoked'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_SUSPENDED, 'Suspended'),
        (STATUS_REVOKED, 'Revoked'),
    ]

    advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name='mailbox_connections',
    )
    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES)
    email_address = models.EmailField()
    # Tokens encrypted at rest (integration rule); stored as opaque blobs
    access_token_enc = models.TextField()
    refresh_token_enc = models.TextField()
    token_expires_at = models.DateTimeField()          # BRU-05
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    # BRU-16: track the last processed message ID to resume idempotently
    sync_cursor = models.CharField(max_length=500, blank=True)

    class Meta:
        unique_together = [('advisor', 'provider', 'email_address')]
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['token_expires_at']),
        ]

    def __str__(self):
        return f"{self.email_address} ({self.provider}) — {self.status}"


class TriggerDomain(TenantBaseModel):
    """FM-07 / BRU-02: sender domains that auto-create leads on inbound email."""
    domain = models.CharField(max_length=253)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [('tenant', 'domain')]

    def __str__(self):
        return self.domain


# ---------------------------------------------------------------------------
# Communication events (FM-10/20)
# ---------------------------------------------------------------------------

class Communication(TenantBaseModel):
    CHANNEL_EMAIL = 'email'
    CHANNEL_SMS = 'sms'
    CHANNEL_CALL = 'call'
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, 'Email'),
        (CHANNEL_SMS, 'SMS'),
        (CHANNEL_CALL, 'Call'),
    ]

    DIRECTION_INBOUND = 'inbound'
    DIRECTION_OUTBOUND = 'outbound'
    DIRECTION_CHOICES = [
        (DIRECTION_INBOUND, 'Inbound'),
        (DIRECTION_OUTBOUND, 'Outbound'),
    ]

    STATUS_QUEUED = 'queued'
    STATUS_SENT = 'sent'
    STATUS_DELIVERED = 'delivered'
    STATUS_FAILED = 'failed'
    STATUS_RECEIVED = 'received'
    STATUS_BOUNCED = 'bounced'
    STATUS_COMPLAINED = 'complained'
    STATUS_CHOICES = [
        (STATUS_QUEUED, 'Queued'),
        (STATUS_SENT, 'Sent'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_RECEIVED, 'Received'),
        (STATUS_BOUNCED, 'Bounced'),
        (STATUS_COMPLAINED, 'Complained'),
    ]

    lead = models.ForeignKey(
        'leads.Lead', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='communications',
    )
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='sent_communications',
    )
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_QUEUED)
    subject = models.CharField(max_length=500, blank=True)
    body = models.TextField(blank=True)                        # inline body text
    body_ref = models.CharField(max_length=500, blank=True)   # storage key, not inline
    external_id = models.CharField(max_length=255, unique=True)   # BRU-16: idempotency key
    scheduled_at = models.DateTimeField(null=True, blank=True)    # BRU-24/42: tz-aware defer
    sent_at = models.DateTimeField(null=True, blank=True)
    is_reply = models.BooleanField(default=False)   # BRU-17: flagged by reply-detection
    campaign_enrollment = models.ForeignKey(
        'campaigns.CampaignEnrollment',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='communications',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'created_at']),
            models.Index(fields=['tenant', 'channel', 'direction']),
            models.Index(fields=['external_id']),
            models.Index(fields=['tenant', 'is_reply']),
            models.Index(fields=['tenant', 'is_reply', 'created_at']),  # today_responses dashboard query
        ]

    def __str__(self):
        return f"{self.channel} {self.direction} [{self.status}] @ {self.created_at:%Y-%m-%d}"


# ---------------------------------------------------------------------------
# Call logs (FM-20 / RingCentral)
# ---------------------------------------------------------------------------

class CallLog(TenantBaseModel):
    """
    FM-20: individual call record.
    BRU-32: recording_consent_captured must be True before recording_ref is stored.
    BRU-19: SMS opt-out keywords handled by suppression service.
    """
    OUTCOME_INTERESTED = 'interested'
    OUTCOME_NOT_INTERESTED = 'not_interested'
    OUTCOME_FOLLOW_UP = 'follow_up'
    OUTCOME_CLOSED = 'closed'
    OUTCOME_NO_ANSWER = 'no_answer'
    OUTCOME_CHOICES = [
        (OUTCOME_INTERESTED, 'Interested'),
        (OUTCOME_NOT_INTERESTED, 'Not Interested'),
        (OUTCOME_FOLLOW_UP, 'Follow Up'),
        (OUTCOME_CLOSED, 'Closed'),
        (OUTCOME_NO_ANSWER, 'No Answer'),
    ]

    communication = models.OneToOneField(
        Communication, on_delete=models.CASCADE, related_name='call_log',
    )
    duration_seconds = models.PositiveIntegerField(default=0)
    outcome = models.CharField(max_length=20, choices=OUTCOME_CHOICES, blank=True)
    recording_ref = models.CharField(max_length=500, blank=True)       # BRU-32: only if consent
    recording_consent_captured = models.BooleanField(default=False)    # BRU-32
    ringcentral_call_id = models.CharField(max_length=255, blank=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'outcome']),
        ]

    def __str__(self):
        return f"Call {self.duration_seconds}s — {self.outcome or 'no outcome'}"


# ---------------------------------------------------------------------------
# Meeting scheduling (FM-19)
# ---------------------------------------------------------------------------

class Meeting(TenantBaseModel):
    lead = models.ForeignKey(
        'leads.Lead', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='meetings',
    )
    advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='meetings',
    )
    scheduled_at = models.DateTimeField()        # stored as UTC; BRU-24: respect recipient tz
    recipient_timezone = models.CharField(max_length=60, default='UTC')  # BRU-24/42
    zoom_link = models.URLField(blank=True)
    zoom_meeting_id = models.CharField(max_length=100, blank=True)
    calendar_provider = models.CharField(max_length=20, blank=True)   # 'google' / 'microsoft'
    calendar_event_id = models.CharField(max_length=255, blank=True)  # BRU-16 idempotency
    outcome = models.CharField(max_length=100, blank=True)
    outcome_recorded_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)
    reminder_sent = models.BooleanField(default=False)

    class Meta:
        ordering = ['-scheduled_at']
        indexes = [
            models.Index(fields=['tenant', 'advisor', 'scheduled_at']),
        ]

    def __str__(self):
        return f"Meeting with {self.lead} @ {self.scheduled_at:%Y-%m-%d %H:%M}"


# ---------------------------------------------------------------------------
# Deliverability & suppression (FM-25, BRU-18/19)
# ---------------------------------------------------------------------------

class SuppressionRecord(TenantBaseModel):
    """
    BRU-19: once suppressed, no automated messages until manually cleared.
    Covers hard bounce, spam complaint, SMS opt-out keyword.
    """
    REASON_HARD_BOUNCE = 'hard_bounce'
    REASON_SPAM_COMPLAINT = 'spam_complaint'
    REASON_SMS_OPTOUT = 'sms_optout'
    REASON_MANUAL = 'manual'
    REASON_CHOICES = [
        (REASON_HARD_BOUNCE, 'Hard Bounce'),
        (REASON_SPAM_COMPLAINT, 'Spam Complaint'),
        (REASON_SMS_OPTOUT, 'SMS Opt-Out Keyword'),
        (REASON_MANUAL, 'Manual Suppression'),
    ]

    CHANNEL_EMAIL = 'email'
    CHANNEL_SMS = 'sms'
    CHANNEL_ALL = 'all'
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, 'Email'),
        (CHANNEL_SMS, 'SMS'),
        (CHANNEL_ALL, 'All Channels'),
    ]

    email = models.EmailField(blank=True, db_index=True)
    phone = models.CharField(max_length=30, blank=True, db_index=True)
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    raw_event = models.JSONField(null=True, blank=True)  # webhook payload for traceability

    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'email', 'channel']),
            models.Index(fields=['tenant', 'phone', 'channel']),
        ]

    def __str__(self):
        target = self.email or self.phone
        return f"Suppressed {target} ({self.channel}) — {self.reason}"


class DeliverabilityEvent(TenantBaseModel):
    """
    FM-25: inbound webhook events from email provider (bounce, complaint, delivery).
    BRU-16: external_id provides idempotency.
    """
    EVENT_BOUNCE = 'bounce'
    EVENT_COMPLAINT = 'complaint'
    EVENT_DELIVERY = 'delivery'
    EVENT_OPEN = 'open'
    EVENT_CLICK = 'click'
    EVENT_CHOICES = [
        (EVENT_BOUNCE, 'Bounce'),
        (EVENT_COMPLAINT, 'Complaint'),
        (EVENT_DELIVERY, 'Delivery'),
        (EVENT_OPEN, 'Open'),
        (EVENT_CLICK, 'Click'),
    ]

    external_id = models.CharField(max_length=255, unique=True)   # BRU-16
    event_type = models.CharField(max_length=20, choices=EVENT_CHOICES)
    email = models.EmailField(db_index=True)
    raw_payload = models.JSONField()
    communication = models.ForeignKey(
        Communication, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='deliverability_events',
    )
    processed = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'event_type', 'processed']),
        ]

    def __str__(self):
        return f"{self.event_type} — {self.email}"


# ---------------------------------------------------------------------------
# Consent & preference management (FM-24, BRU-07/15)
# ---------------------------------------------------------------------------

class ConsentPreference(TenantBaseModel):
    """
    FM-24: system-of-record for channel + purpose consent.
    Append-only history; latest record per (lead/client, channel, purpose) is the truth.
    BRU-07: once revoked, no automated messages on that channel until re-granted.
    BRU-38: legal hold can block deletion.
    """
    STATE_GRANTED = 'granted'
    STATE_REVOKED = 'revoked'
    STATE_PENDING = 'pending'
    STATE_CHOICES = [
        (STATE_GRANTED, 'Granted'),
        (STATE_REVOKED, 'Revoked'),
        (STATE_PENDING, 'Pending'),
    ]

    CHANNEL_EMAIL = 'email'
    CHANNEL_SMS = 'sms'
    CHANNEL_CALL = 'call'
    CHANNEL_ALL = 'all'
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, 'Email'),
        (CHANNEL_SMS, 'SMS'),
        (CHANNEL_CALL, 'Call'),
        (CHANNEL_ALL, 'All Channels'),
    ]

    lead = models.ForeignKey(
        'leads.Lead', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='consent_preferences',
    )
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES)
    purpose = models.CharField(max_length=100)      # e.g. 'marketing', 'transactional'
    state = models.CharField(max_length=20, choices=STATE_CHOICES)
    source = models.CharField(max_length=200)       # e.g. 'web_form', 'opt_out_link', 'sms_keyword'
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    is_under_legal_hold = models.BooleanField(default=False)   # BRU-38

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'channel', 'state']),
            models.Index(fields=['tenant', 'lead', 'channel']),
        ]

    def __str__(self):
        return f"{self.lead} — {self.channel} {self.state} ({self.purpose})"
