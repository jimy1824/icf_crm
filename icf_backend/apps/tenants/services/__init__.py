import datetime
import logging

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import AuditService
from apps.common.events import event_bus
from apps.tenants.models import (
    BillingRecord,
    NotificationPreference,
    SubscriptionPlan,
    Tenant,
    TenantBranding,
    TenantSubscription,
)

logger = logging.getLogger(__name__)

# BRU-23: grace period length in days before degradation
GRACE_PERIOD_DAYS = 14


# ---------------------------------------------------------------------------
# Tenant lifecycle (FM-01)
# ---------------------------------------------------------------------------

@transaction.atomic
def create_tenant(
    *, firm_name, region='', timezone_name='America/New_York', plan_id, actor=None,
    is_trial=False, trial_days=14,
    legal_name='', website='', company_email='', phone='',
    address_line1='', city='', state='', country='US', postal_code='',
):
    plan = SubscriptionPlan.objects.get(id=plan_id)
    tenant = Tenant(
        firm_name=firm_name, region=region, timezone=timezone_name,
        legal_name=legal_name, website=website, company_email=company_email,
        phone=phone, address_line1=address_line1, city=city, state=state,
        country=country, postal_code=postal_code,
    )
    tenant.full_clean()
    tenant.save()

    today = datetime.date.today()
    trial_expires = (today + datetime.timedelta(days=trial_days)) if is_trial else None
    TenantSubscription.objects.create(
        tenant=tenant,
        plan=plan,
        status=TenantSubscription.STATUS_TRIAL if is_trial else TenantSubscription.STATUS_ACTIVE,
        is_trial=is_trial,
        trial_expires_at=trial_expires,
        starts_at=today,
    )
    AuditService.log(
        tenant=tenant, actor=actor, action='tenant.created',
        entity_type='Tenant', entity_id=tenant.pk,
        after_state={
            'firm_name': firm_name, 'plan': plan.name,
            'is_trial': is_trial,
        },
    )
    return tenant


def suspend_tenant(*, tenant, actor=None):
    """BRU-10: halts automation, preserves data."""
    tenant.status = Tenant.STATUS_SUSPENDED
    tenant.save(update_fields=['status', 'updated_at'])
    AuditService.log(
        tenant=tenant, actor=actor, action='tenant.suspended',
        entity_type='Tenant', entity_id=tenant.pk,
    )
    return tenant


def activate_tenant(*, tenant, actor=None):
    """Re-activate a suspended tenant."""
    tenant.status = Tenant.STATUS_ACTIVE
    tenant.save(update_fields=['status', 'updated_at'])
    AuditService.log(
        tenant=tenant, actor=actor, action='tenant.activated',
        entity_type='Tenant', entity_id=tenant.pk,
    )
    return tenant


def disable_login(*, tenant, actor=None):
    """Super Admin: lock out all users of a tenant immediately."""
    tenant.login_disabled = True
    tenant.save(update_fields=['login_disabled', 'updated_at'])
    AuditService.log(
        tenant=tenant, actor=actor, action='tenant.login_disabled',
        entity_type='Tenant', entity_id=tenant.pk,
    )
    return tenant


def enable_login(*, tenant, actor=None):
    """Super Admin: re-enable logins for a tenant."""
    tenant.login_disabled = False
    tenant.save(update_fields=['login_disabled', 'updated_at'])
    AuditService.log(
        tenant=tenant, actor=actor, action='tenant.login_enabled',
        entity_type='Tenant', entity_id=tenant.pk,
    )
    return tenant


@transaction.atomic
def update_tenant_profile(*, tenant, actor=None, **fields):
    """
    Update company profile fields on a tenant.
    Accepted fields: legal_name, registration_number, tax_number, website,
    company_email, phone, logo_url, address_line1, address_line2, city, state,
    country, postal_code, subdomain, custom_domain, firm_name, region, timezone.
    BRU-01: actors in a different tenant may NOT call this.
    """
    ALLOWED = {
        'firm_name', 'legal_name', 'registration_number', 'tax_number',
        'website', 'company_email', 'phone', 'logo_url',
        'address_line1', 'address_line2', 'city', 'state', 'country', 'postal_code',
        'subdomain', 'custom_domain', 'region', 'timezone',
    }
    before = {f: getattr(tenant, f) for f in ALLOWED if hasattr(tenant, f)}
    for field, value in fields.items():
        if field in ALLOWED:
            setattr(tenant, field, value)
    tenant.full_clean()
    tenant.save()
    AuditService.log(
        tenant=tenant, actor=actor, action='tenant.profile_updated',
        entity_type='Tenant', entity_id=tenant.pk,
        before_state={k: str(v) for k, v in before.items() if k in fields},
        after_state={k: str(v) for k, v in fields.items() if k in ALLOWED},
    )
    return tenant


# ---------------------------------------------------------------------------
# Branding (FM-01 white-label)
# ---------------------------------------------------------------------------

class BrandingService:

    @staticmethod
    def get_or_create(tenant) -> TenantBranding:
        branding, _ = TenantBranding.objects.get_or_create(tenant=tenant)
        return branding

    @staticmethod
    @transaction.atomic
    def update(*, tenant, actor, **fields) -> TenantBranding:
        ALLOWED = {
            'primary_color', 'secondary_color', 'login_bg_url',
            'custom_smtp_host', 'custom_smtp_port', 'custom_smtp_user',
            'custom_sms_provider',
        }
        branding = BrandingService.get_or_create(tenant)
        before = {f: getattr(branding, f) for f in ALLOWED}
        for field, value in fields.items():
            if field in ALLOWED:
                setattr(branding, field, value)
        branding.save()
        AuditService.log(
            tenant=tenant, actor=actor, action='tenant.branding_updated',
            entity_type='TenantBranding', entity_id=branding.pk,
            before_state={k: str(v) for k, v in before.items() if k in fields},
            after_state={k: str(v) for k, v in fields.items() if k in ALLOWED},
        )
        return branding


# ---------------------------------------------------------------------------
# Subscription / plan management (FM-02, BRU-04/13)
# ---------------------------------------------------------------------------

class SubscriptionService:

    @staticmethod
    def check_lead_limit(*, tenant) -> bool:
        """BRU-04: True if tenant is within plan lead limit."""
        sub = _get_subscription(tenant)
        if not sub:
            return True
        from apps.leads.models import Lead
        count = Lead.objects.filter(tenant=tenant).count()
        return count < sub.plan.max_leads

    @staticmethod
    def check_user_limit(*, tenant) -> bool:
        """BRU-04: True if tenant is within plan user limit."""
        sub = _get_subscription(tenant)
        if not sub:
            return True
        from apps.users.models import CustomUser
        count = CustomUser.objects.filter(tenant=tenant, is_active=True).count()
        return count < sub.plan.max_users

    @staticmethod
    def check_campaign_limit(*, tenant) -> bool:
        """BRU-04: True if tenant is within plan campaign limit. 0 = unlimited."""
        sub = _get_subscription(tenant)
        if not sub:
            return True
        limit = sub.plan.max_campaigns
        if limit == 0:
            return True
        from apps.campaigns.models import Campaign
        count = Campaign.objects.filter(tenant=tenant).count()
        return count < limit

    @staticmethod
    def enforce_lead_limit(*, tenant) -> None:
        """BRU-04: raise ValidationError if limit exceeded."""
        if not SubscriptionService.check_lead_limit(tenant=tenant):
            sub = _get_subscription(tenant)
            raise ValidationError(
                f"BRU-04: Lead limit ({sub.plan.max_leads}) reached for this plan. "
                "Upgrade to add more leads."
            )

    @staticmethod
    def enforce_user_limit(*, tenant) -> None:
        """BRU-04: raise ValidationError if user limit exceeded."""
        if not SubscriptionService.check_user_limit(tenant=tenant):
            sub = _get_subscription(tenant)
            raise ValidationError(
                f"BRU-04: User limit ({sub.plan.max_users}) reached for this plan. "
                "Upgrade to add more users."
            )

    @staticmethod
    def enforce_campaign_limit(*, tenant) -> None:
        """BRU-04: raise ValidationError if campaign limit exceeded."""
        if not SubscriptionService.check_campaign_limit(tenant=tenant):
            sub = _get_subscription(tenant)
            raise ValidationError(
                f"BRU-04: Campaign limit ({sub.plan.max_campaigns}) reached for this plan. "
                "Upgrade to create more campaigns."
            )

    @staticmethod
    @transaction.atomic
    def assign_plan(*, tenant, plan, actor) -> TenantSubscription:
        """
        BRU-13: downgrade checks current usage; never silently deletes data.
        If new plan limits are below current usage, raises ValidationError.
        """
        from apps.leads.models import Lead
        from apps.users.models import CustomUser
        from apps.campaigns.models import Campaign

        current_leads = Lead.objects.filter(tenant=tenant).count()
        current_users = CustomUser.objects.filter(tenant=tenant, is_active=True).count()
        current_campaigns = Campaign.objects.filter(tenant=tenant).count()

        if current_leads > plan.max_leads:
            raise ValidationError(
                f"BRU-13: Cannot downgrade — tenant has {current_leads} leads "
                f"but new plan allows only {plan.max_leads}."
            )
        if current_users > plan.max_users:
            raise ValidationError(
                f"BRU-13: Cannot downgrade — tenant has {current_users} active users "
                f"but new plan allows only {plan.max_users}."
            )
        if plan.max_campaigns > 0 and current_campaigns > plan.max_campaigns:
            raise ValidationError(
                f"BRU-13: Cannot downgrade — tenant has {current_campaigns} campaigns "
                f"but new plan allows only {plan.max_campaigns}."
            )

        sub, created = TenantSubscription.objects.get_or_create(
            tenant=tenant,
            defaults={'plan': plan, 'starts_at': datetime.date.today()},
        )
        if not created:
            old_plan = sub.plan.name
            sub.plan = plan
            sub.status = TenantSubscription.STATUS_ACTIVE
            sub.is_trial = False
            sub.save(update_fields=['plan', 'status', 'is_trial', 'updated_at'])
            AuditService.log(
                tenant=tenant, actor=actor, action='subscription.plan_changed',
                entity_type='TenantSubscription', entity_id=sub.pk,
                before_state={'plan': old_plan},
                after_state={'plan': plan.name},
            )
        return sub

    @staticmethod
    @transaction.atomic
    def start_trial(*, tenant, plan, trial_days: int = 14, actor=None) -> TenantSubscription:
        """Start or extend a trial subscription for a tenant."""
        today = datetime.date.today()
        trial_expires = today + datetime.timedelta(days=trial_days)
        sub, created = TenantSubscription.objects.get_or_create(
            tenant=tenant,
            defaults={
                'plan': plan,
                'status': TenantSubscription.STATUS_TRIAL,
                'is_trial': True,
                'trial_expires_at': trial_expires,
                'starts_at': today,
            },
        )
        if not created:
            sub.plan = plan
            sub.status = TenantSubscription.STATUS_TRIAL
            sub.is_trial = True
            sub.trial_expires_at = trial_expires
            sub.save(update_fields=['plan', 'status', 'is_trial', 'trial_expires_at', 'updated_at'])
        AuditService.log(
            tenant=tenant, actor=actor, action='subscription.trial_started',
            entity_type='TenantSubscription', entity_id=sub.pk,
            after_state={'trial_expires_at': str(trial_expires), 'plan': plan.name},
        )
        return sub

    @staticmethod
    @transaction.atomic
    def extend_trial(*, tenant, days: int, actor=None) -> TenantSubscription:
        """Super Admin: extend trial period by N additional days."""
        sub = _get_subscription(tenant)
        if not sub:
            raise ValidationError("No subscription found for this tenant.")
        if not sub.is_trial:
            raise ValidationError("Tenant is not on a trial subscription.")
        base = sub.trial_expires_at or datetime.date.today()
        sub.trial_expires_at = base + datetime.timedelta(days=days)
        sub.save(update_fields=['trial_expires_at', 'updated_at'])
        AuditService.log(
            tenant=tenant, actor=actor, action='tenant.trial_extended',
            entity_type='TenantSubscription', entity_id=sub.pk,
            after_state={'trial_expires_at': str(sub.trial_expires_at), 'days_added': days},
        )
        return sub

    @staticmethod
    def get_usage_summary(*, tenant) -> dict:
        """FM-02: returns current usage vs. plan limits."""
        from apps.leads.models import Lead
        from apps.users.models import CustomUser
        from apps.campaigns.models import Campaign
        sub = _get_subscription(tenant)
        plan = sub.plan if sub else None
        return {
            'leads': {
                'current': Lead.objects.filter(tenant=tenant).count(),
                'limit': plan.max_leads if plan else None,
            },
            'users': {
                'current': CustomUser.objects.filter(tenant=tenant, is_active=True).count(),
                'limit': plan.max_users if plan else None,
            },
            'campaigns': {
                'current': Campaign.objects.filter(tenant=tenant).count(),
                'limit': plan.max_campaigns if plan else None,
            },
            'plan': plan.name if plan else None,
            'subscription_status': sub.status if sub else None,
            'is_trial': sub.is_trial if sub else False,
            'trial_expires_at': str(sub.trial_expires_at) if (sub and sub.trial_expires_at) else None,
        }


# ---------------------------------------------------------------------------
# Billing / dunning (FM-03, BRU-23)
# ---------------------------------------------------------------------------

class BillingService:

    @staticmethod
    @transaction.atomic
    def record_invoice(
        *, tenant, amount_cents, currency, period_start, period_end,
        external_invoice_id='', invoice_number='', tax_amount_cents=0,
        discount_amount_cents=0, actor=None,
    ) -> BillingRecord:
        # BRU-16: idempotency — skip if record already exists for this period/external_id
        if external_invoice_id:
            existing = BillingRecord.objects.filter(
                tenant=tenant,
                external_invoice_id=external_invoice_id,
            ).first()
            if existing:
                return existing

        record = BillingRecord.objects.create(
            tenant=tenant,
            record_type=BillingRecord.TYPE_INVOICE,
            status=BillingRecord.STATUS_PENDING,
            amount_cents=amount_cents,
            currency=currency,
            period_start=period_start,
            period_end=period_end,
            external_invoice_id=external_invoice_id,
            invoice_number=invoice_number,
            tax_amount_cents=tax_amount_cents,
            discount_amount_cents=discount_amount_cents,
        )
        # BRU-23: start grace period on unpaid invoice
        sub = _get_subscription(tenant)
        if sub:
            grace_end = datetime.date.today() + datetime.timedelta(days=GRACE_PERIOD_DAYS)
            sub.payment_due_date = period_end
            sub.grace_period_ends_at = grace_end
            sub.status = TenantSubscription.STATUS_ACTIVE
            sub.save(update_fields=['payment_due_date', 'grace_period_ends_at', 'status', 'updated_at'])
        event_bus.emit('billing.invoice_generated', tenant_id=tenant.pk, record_id=record.pk)
        return record

    @staticmethod
    @transaction.atomic
    def record_payment(
        *, tenant, billing_record: BillingRecord,
        payment_method='', transaction_id='', actor=None,
    ) -> BillingRecord:
        billing_record.status = BillingRecord.STATUS_PAID
        billing_record.paid_at = timezone.now()
        if payment_method:
            billing_record.payment_method = payment_method
        if transaction_id:
            billing_record.transaction_id = transaction_id
        billing_record.save(
            update_fields=['status', 'paid_at', 'payment_method', 'transaction_id', 'updated_at']
        )
        # Clear dunning state
        sub = _get_subscription(tenant)
        if sub:
            sub.status = TenantSubscription.STATUS_ACTIVE
            sub.payment_due_date = None
            sub.grace_period_ends_at = None
            sub.save(update_fields=['status', 'payment_due_date', 'grace_period_ends_at', 'updated_at'])
        AuditService.log(
            tenant=tenant, actor=actor, action='billing.payment_received',
            entity_type='BillingRecord', entity_id=billing_record.pk,
            after_state={'amount_cents': billing_record.amount_cents},
        )
        return billing_record

    @staticmethod
    @transaction.atomic
    def apply_dunning(*, tenant, actor=None) -> TenantSubscription:
        """
        BRU-23: grace period expired → read-only → suspended.
        Called by Celery beat job daily.
        """
        sub = _get_subscription(tenant)
        if not sub:
            return None
        today = datetime.date.today()
        if sub.status == TenantSubscription.STATUS_ACTIVE and sub.grace_period_ends_at:
            if today > sub.grace_period_ends_at:
                sub.status = TenantSubscription.STATUS_READ_ONLY
                sub.save(update_fields=['status', 'updated_at'])
                event_bus.emit(
                    'billing.degraded_to_read_only',
                    tenant_id=tenant.pk,
                )
                logger.warning("Tenant %d degraded to read-only (BRU-23)", tenant.pk)
        elif sub.status == TenantSubscription.STATUS_READ_ONLY and sub.grace_period_ends_at:
            suspend_threshold = sub.grace_period_ends_at + datetime.timedelta(days=7)
            if today > suspend_threshold:
                sub.status = TenantSubscription.STATUS_SUSPENDED
                sub.save(update_fields=['status', 'updated_at'])
                tenant.status = Tenant.STATUS_SUSPENDED
                tenant.save(update_fields=['status', 'updated_at'])
                event_bus.emit(
                    'billing.tenant_suspended',
                    tenant_id=tenant.pk,
                )
                logger.warning("Tenant %d suspended for non-payment (BRU-23)", tenant.pk)
        AuditService.log(
            tenant=tenant, actor=actor, action='billing.dunning_applied',
            entity_type='TenantSubscription', entity_id=sub.pk,
            after_state={'status': sub.status},
        )
        return sub

    @staticmethod
    def is_read_only(*, tenant) -> bool:
        """BRU-23: check if tenant is in read-only or suspended state."""
        sub = _get_subscription(tenant)
        if not sub:
            return False
        return sub.status in (TenantSubscription.STATUS_READ_ONLY, TenantSubscription.STATUS_SUSPENDED)

    @staticmethod
    @transaction.atomic
    def generate_renewal_invoice(*, tenant, actor=None) -> BillingRecord | None:
        """
        Generate a renewal invoice for a tenant whose subscription ends within 3 days.
        BRU-16: idempotent — skips if invoice already exists for the upcoming period.
        Called by Celery beat task.
        """
        sub = _get_subscription(tenant)
        if not sub or sub.status not in (
            TenantSubscription.STATUS_ACTIVE,
        ):
            return None
        if not sub.ends_at:
            return None

        today = datetime.date.today()
        if (sub.ends_at - today).days > 3:
            return None

        # Compute next period
        if sub.billing_cycle == TenantSubscription.CYCLE_MONTHLY:
            delta = datetime.timedelta(days=30)
        elif sub.billing_cycle == TenantSubscription.CYCLE_QUARTERLY:
            delta = datetime.timedelta(days=91)
        else:
            delta = datetime.timedelta(days=365)

        period_start = sub.ends_at
        period_end = sub.ends_at + delta
        ext_id = f"renewal-{tenant.pk}-{period_start}"

        record = BillingService.record_invoice(
            tenant=tenant,
            amount_cents=0,  # actual price set by Super Admin; 0 = placeholder
            currency='USD',
            period_start=period_start,
            period_end=period_end,
            external_invoice_id=ext_id,
            actor=actor,
        )
        # Advance subscription end date
        sub.ends_at = period_end
        sub.save(update_fields=['ends_at', 'updated_at'])
        return record


# ---------------------------------------------------------------------------
# Notification preferences (FM-14)
# ---------------------------------------------------------------------------

class NotificationPreferenceService:

    @staticmethod
    def get_or_create_preference(*, user, event_type) -> NotificationPreference:
        pref, _ = NotificationPreference.objects.get_or_create(
            user=user, event_type=event_type,
        )
        return pref

    @staticmethod
    @transaction.atomic
    def update_preference(*, user, event_type, **channel_flags) -> NotificationPreference:
        pref = NotificationPreferenceService.get_or_create_preference(
            user=user, event_type=event_type,
        )
        allowed = {'email_enabled', 'sms_enabled', 'in_app_enabled', 'push_enabled'}
        for field, val in channel_flags.items():
            if field in allowed:
                setattr(pref, field, val)
        pref.save()
        return pref

    @staticmethod
    def enabled_channels(*, user, event_type) -> list:
        """Returns list of channel strings the user wants for this event_type."""
        try:
            pref = NotificationPreference.objects.get(user=user, event_type=event_type)
        except NotificationPreference.DoesNotExist:
            return ['in_app']
        channels = []
        if pref.in_app_enabled:
            channels.append('in_app')
        if pref.email_enabled:
            channels.append('email')
        if pref.sms_enabled:
            channels.append('sms')
        if pref.push_enabled:
            channels.append('push')
        return channels or ['in_app']


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_subscription(tenant) -> TenantSubscription | None:
    return TenantSubscription.objects.filter(tenant=tenant).select_related('plan').first()
