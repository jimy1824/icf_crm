import logging

from config.celery import app

logger = logging.getLogger(__name__)


@app.task(name='tenants.anonymize_deleted_tenant', queue='default')
def anonymize_deleted_tenant(tenant_id):
    # BRU-11: triggered when a tenant is marked STATUS_DELETED
    pass


@app.task(bind=True, max_retries=2, default_retry_delay=60, queue='billing',
          name='apps.tenants.tasks.run_dunning_sweep')
def run_dunning_sweep(self):
    """
    BRU-23: daily sweep that degrades tenants with unpaid invoices past grace period.
    Idempotent — apply_dunning reads current state each time.
    """
    from apps.tenants.models import TenantSubscription
    from apps.tenants.services import BillingService

    subs = TenantSubscription.objects.select_related('tenant').filter(
        status__in=(
            TenantSubscription.STATUS_ACTIVE,
            TenantSubscription.STATUS_READ_ONLY,
        ),
        grace_period_ends_at__isnull=False,
    )
    for sub in subs:
        try:
            BillingService.apply_dunning(tenant=sub.tenant)
        except Exception:
            logger.exception("Dunning sweep failed for tenant %d", sub.tenant_id)


@app.task(bind=True, max_retries=2, default_retry_delay=60, queue='billing',
          name='apps.tenants.tasks.generate_subscription_renewals')
def generate_subscription_renewals(self):
    """
    Daily beat task: generate renewal invoices for subscriptions ending within 3 days.
    BRU-16: BillingService.generate_renewal_invoice is idempotent.
    """
    import datetime
    from apps.tenants.models import TenantSubscription
    from apps.tenants.services import BillingService

    soon = datetime.date.today() + datetime.timedelta(days=3)
    subs = TenantSubscription.objects.select_related('tenant').filter(
        status=TenantSubscription.STATUS_ACTIVE,
        ends_at__isnull=False,
        ends_at__lte=soon,
    )
    for sub in subs:
        try:
            BillingService.generate_renewal_invoice(tenant=sub.tenant)
        except Exception:
            logger.exception(
                "Renewal invoice generation failed for tenant %d", sub.tenant_id,
            )


@app.task(bind=True, max_retries=2, default_retry_delay=60, queue='billing',
          name='apps.tenants.tasks.poll_trial_expirations')
def poll_trial_expirations(self):
    """
    Daily beat task: detect expired trials and move them to grace_period status.
    BRU-16: idempotent — already-expired trials are filtered by status.
    """
    import datetime
    from apps.tenants.models import TenantSubscription
    from apps.audit.services import AuditService

    today = datetime.date.today()
    expired = TenantSubscription.objects.select_related('tenant').filter(
        status=TenantSubscription.STATUS_TRIAL,
        trial_expires_at__lt=today,
    )
    for sub in expired:
        try:
            sub.status = TenantSubscription.STATUS_GRACE
            sub.save(update_fields=['status', 'updated_at'])
            from apps.common.events import event_bus
            event_bus.emit('subscription.trial_expired', tenant_id=sub.tenant_id)
            AuditService.log(
                tenant=sub.tenant, actor=None,
                action='subscription.trial_expired',
                entity_type='TenantSubscription', entity_id=sub.pk,
                after_state={'trial_expires_at': str(sub.trial_expires_at)},
            )
            logger.info("Trial expired for tenant %d", sub.tenant_id)
        except Exception:
            logger.exception("Trial expiry processing failed for tenant %d", sub.tenant_id)
