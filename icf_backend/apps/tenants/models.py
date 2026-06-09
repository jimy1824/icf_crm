from django.conf import settings
from django.db import models
from apps.common.models import BaseModel


class Tenant(BaseModel):
    STATUS_ACTIVE = 'active'
    STATUS_SUSPENDED = 'suspended'
    STATUS_DELETED = 'deleted'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_SUSPENDED, 'Suspended'),
        (STATUS_DELETED, 'Deleted'),
    ]

    DOMAIN_STATUS_PENDING = 'pending'
    DOMAIN_STATUS_ACTIVE = 'active'
    DOMAIN_STATUS_FAILED = 'failed'
    DOMAIN_STATUS_CHOICES = [
        (DOMAIN_STATUS_PENDING, 'Pending'),
        (DOMAIN_STATUS_ACTIVE, 'Active'),
        (DOMAIN_STATUS_FAILED, 'Failed'),
    ]

    # --- Core (existing) ---
    firm_name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    region = models.CharField(max_length=100, blank=True)
    timezone = models.CharField(max_length=63, default='America/New_York')

    # --- Extended company profile ---
    legal_name = models.CharField(max_length=200, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    tax_number = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    company_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=30, blank=True)
    logo_url = models.URLField(blank=True)

    # --- Address ---
    address_line1 = models.CharField(max_length=200, blank=True)
    address_line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True, default='US')
    postal_code = models.CharField(max_length=20, blank=True)

    # --- Domain configuration ---
    subdomain = models.SlugField(max_length=100, blank=True, unique=True, null=True)
    custom_domain = models.CharField(max_length=255, blank=True)
    domain_status = models.CharField(
        max_length=10, choices=DOMAIN_STATUS_CHOICES, default=DOMAIN_STATUS_PENDING,
    )

    # --- Access control ---
    login_disabled = models.BooleanField(default=False)

    class Meta:
        ordering = ['firm_name']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['subdomain']),
        ]

    def __str__(self):
        return self.firm_name


class SubscriptionPlan(BaseModel):
    name = models.CharField(max_length=100, unique=True)
    max_leads = models.PositiveIntegerField()
    max_users = models.PositiveIntegerField()
    max_storage_gb = models.PositiveIntegerField()
    max_campaigns = models.PositiveIntegerField(default=0, help_text='0 = unlimited')
    features = models.JSONField(default=dict)

    def __str__(self):
        return self.name


class TenantSubscription(BaseModel):
    STATUS_ACTIVE = 'active'
    STATUS_TRIAL = 'trial'
    STATUS_GRACE = 'grace_period'
    STATUS_READ_ONLY = 'read_only'
    STATUS_SUSPENDED = 'suspended'
    STATUS_CANCELLED = 'cancelled'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_TRIAL, 'Trial'),
        (STATUS_GRACE, 'Grace Period'),
        (STATUS_READ_ONLY, 'Read Only'),
        (STATUS_SUSPENDED, 'Suspended'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    CYCLE_MONTHLY = 'monthly'
    CYCLE_QUARTERLY = 'quarterly'
    CYCLE_YEARLY = 'yearly'
    CYCLE_CHOICES = [
        (CYCLE_MONTHLY, 'Monthly'),
        (CYCLE_QUARTERLY, 'Quarterly'),
        (CYCLE_YEARLY, 'Yearly'),
    ]

    tenant = models.OneToOneField(
        Tenant, on_delete=models.CASCADE, related_name='subscription'
    )
    plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.PROTECT, related_name='subscriptions'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    billing_cycle = models.CharField(
        max_length=10, choices=CYCLE_CHOICES, default=CYCLE_MONTHLY,
    )
    starts_at = models.DateField()
    ends_at = models.DateField(null=True, blank=True)

    # Trial
    is_trial = models.BooleanField(default=False)
    trial_expires_at = models.DateField(null=True, blank=True)

    # BRU-23: dunning
    payment_due_date = models.DateField(null=True, blank=True)
    grace_period_ends_at = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.tenant.firm_name} — {self.plan.name}"


class TenantBranding(BaseModel):
    """
    White-label configuration for a tenant.
    Lazy-created on first access. Future-ready — fields stored now, used later.
    """
    tenant = models.OneToOneField(
        Tenant, on_delete=models.CASCADE, related_name='branding',
    )
    primary_color = models.CharField(max_length=7, default='#1A56DB')
    secondary_color = models.CharField(max_length=7, default='#6B7280')
    login_bg_url = models.URLField(blank=True)
    custom_smtp_host = models.CharField(max_length=255, blank=True)
    custom_smtp_port = models.PositiveSmallIntegerField(default=587)
    custom_smtp_user = models.CharField(max_length=255, blank=True)
    custom_sms_provider = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Branding for {self.tenant.firm_name}"


class BillingRecord(BaseModel):
    """
    FM-03: invoice / payment event.
    BRU-23: non-payment triggers grace → read-only → suspended.
    """
    TYPE_INVOICE = 'invoice'
    TYPE_PAYMENT = 'payment'
    TYPE_REFUND = 'refund'
    TYPE_CHOICES = [
        (TYPE_INVOICE, 'Invoice'),
        (TYPE_PAYMENT, 'Payment'),
        (TYPE_REFUND, 'Refund'),
    ]

    STATUS_PENDING = 'pending'
    STATUS_PAID = 'paid'
    STATUS_FAILED = 'failed'
    STATUS_REFUNDED = 'refunded'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PAID, 'Paid'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_REFUNDED, 'Refunded'),
    ]

    PAYMENT_METHOD_CARD = 'card'
    PAYMENT_METHOD_BANK = 'bank_transfer'
    PAYMENT_METHOD_CHECK = 'check'
    PAYMENT_METHOD_OTHER = 'other'
    PAYMENT_METHOD_CHOICES = [
        (PAYMENT_METHOD_CARD, 'Card'),
        (PAYMENT_METHOD_BANK, 'Bank Transfer'),
        (PAYMENT_METHOD_CHECK, 'Check'),
        (PAYMENT_METHOD_OTHER, 'Other'),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='billing_records')
    record_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default='USD')
    period_start = models.DateField()
    period_end = models.DateField()
    external_invoice_id = models.CharField(max_length=255, blank=True, db_index=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    # Extended billing detail
    invoice_number = models.CharField(max_length=100, blank=True)
    tax_amount_cents = models.PositiveIntegerField(default=0)
    discount_amount_cents = models.PositiveIntegerField(default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES, blank=True)
    transaction_id = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'record_type']),
        ]

    def __str__(self):
        return f"{self.tenant.firm_name} {self.record_type} {self.amount_cents/100:.2f} {self.currency}"


class NotificationPreference(BaseModel):
    """
    FM-14: per-user, per-event-type channel preferences.
    BRU-07/15: consent gate — disabling a channel here suppresses that channel.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences',
    )
    event_type = models.CharField(max_length=100)
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    in_app_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=False)

    class Meta:
        unique_together = [('user', 'event_type')]

    def __str__(self):
        return f"{self.user_id} — {self.event_type}"
