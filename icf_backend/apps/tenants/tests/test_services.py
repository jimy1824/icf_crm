"""
Tests for Phase 4 tenant services.
BRU-04: plan limit enforcement
BRU-13: downgrade blocked when usage exceeds new plan limits
BRU-23: dunning state machine (grace → read-only → suspended)
"""
import datetime

import pytest
from django.core.exceptions import ValidationError

from apps.tenants.models import (
    BillingRecord, SubscriptionPlan, Tenant, TenantSubscription,
)
from apps.tenants.services import BillingService, SubscriptionService


@pytest.fixture
def starter_plan(db):
    return SubscriptionPlan.objects.create(
        name='Starter', max_leads=5, max_users=2, max_storage_gb=5,
    )


@pytest.fixture
def pro_plan(db):
    return SubscriptionPlan.objects.create(
        name='Pro', max_leads=50, max_users=10, max_storage_gb=50,
    )


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm')


@pytest.fixture
def subscription(db, tenant, starter_plan):
    return TenantSubscription.objects.create(
        tenant=tenant, plan=starter_plan, starts_at=datetime.date.today(),
    )


# ---------------------------------------------------------------------------
# BRU-04: Plan limit enforcement
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSubscriptionServiceLimits:

    def test_check_lead_limit_within_limit(self, subscription, tenant):
        # No leads created → within limit
        assert SubscriptionService.check_lead_limit(tenant=tenant) is True

    def test_enforce_lead_limit_raises_when_at_limit(self, subscription, tenant, starter_plan):
        from apps.leads.models import Lead
        # Saturate the limit
        for i in range(starter_plan.max_leads):
            Lead.objects.create(
                tenant=tenant,
                first_name='A',
                last_name=f'Lead{i}',
                email=f'lead{i}@x.com',
                status=Lead.STATUS_LEAD,
            )
        with pytest.raises(ValidationError, match='BRU-04'):
            SubscriptionService.enforce_lead_limit(tenant=tenant)

    def test_check_lead_limit_within_returns_false_when_full(self, subscription, tenant, starter_plan):
        from apps.leads.models import Lead
        for i in range(starter_plan.max_leads):
            Lead.objects.create(
                tenant=tenant,
                first_name='A', last_name=f'L{i}',
                email=f'l{i}@x.com',
                status=Lead.STATUS_LEAD,
            )
        assert SubscriptionService.check_lead_limit(tenant=tenant) is False

    def test_check_user_limit_within_limit(self, subscription, tenant):
        assert SubscriptionService.check_user_limit(tenant=tenant) is True

    def test_enforce_user_limit_raises_when_at_limit(self, subscription, tenant, starter_plan):
        from apps.users.models import CustomUser
        for i in range(starter_plan.max_users):
            CustomUser.objects.create_user(
                email=f'user{i}@firm.com',
                password='pass',
                tenant=tenant,
                role=CustomUser.ROLE_ADVISOR,
                first_name='U', last_name=f'{i}',
            )
        with pytest.raises(ValidationError, match='BRU-04'):
            SubscriptionService.enforce_user_limit(tenant=tenant)

    def test_get_usage_summary(self, subscription, tenant, starter_plan):
        summary = SubscriptionService.get_usage_summary(tenant=tenant)
        assert summary['leads']['limit'] == starter_plan.max_leads
        assert summary['users']['limit'] == starter_plan.max_users
        assert summary['plan'] == 'Starter'


# ---------------------------------------------------------------------------
# BRU-13: Downgrade policy
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestSubscriptionServiceDowngrade:

    def test_assign_plan_upgrade_succeeds(self, subscription, tenant, pro_plan):
        from apps.users.models import CustomUser
        actor = CustomUser.objects.create_user(
            email='admin@firm.com', password='pass',
            tenant=tenant, role=CustomUser.ROLE_SUPER_ADMIN,
            first_name='A', last_name='B',
        )
        sub = SubscriptionService.assign_plan(tenant=tenant, plan=pro_plan, actor=actor)
        assert sub.plan == pro_plan

    def test_assign_plan_downgrade_blocked_by_leads(self, subscription, tenant, starter_plan, pro_plan):
        from apps.leads.models import Lead
        from apps.users.models import CustomUser
        actor = CustomUser.objects.create_user(
            email='admin@firm.com', password='pass',
            tenant=tenant, role=CustomUser.ROLE_SUPER_ADMIN,
            first_name='A', last_name='B',
        )
        # First upgrade
        subscription.plan = pro_plan
        subscription.save()
        # Create more leads than starter allows
        for i in range(starter_plan.max_leads + 1):
            Lead.objects.create(
                tenant=tenant, first_name='A', last_name=f'L{i}',
                email=f'l{i}@x.com', status=Lead.STATUS_LEAD,
            )
        with pytest.raises(ValidationError, match='BRU-13'):
            SubscriptionService.assign_plan(tenant=tenant, plan=starter_plan, actor=actor)

    def test_assign_plan_downgrade_blocked_by_users(self, subscription, tenant, starter_plan, pro_plan):
        from apps.users.models import CustomUser
        actor = CustomUser.objects.create_user(
            email='admin@firm.com', password='pass',
            tenant=tenant, role=CustomUser.ROLE_SUPER_ADMIN,
            first_name='A', last_name='B',
        )
        subscription.plan = pro_plan
        subscription.save()
        for i in range(starter_plan.max_users + 1):
            CustomUser.objects.create_user(
                email=f'u{i}@firm.com', password='pass',
                tenant=tenant, role=CustomUser.ROLE_ADVISOR,
                first_name='U', last_name=f'{i}',
            )
        with pytest.raises(ValidationError, match='BRU-13'):
            SubscriptionService.assign_plan(tenant=tenant, plan=starter_plan, actor=actor)


# ---------------------------------------------------------------------------
# BRU-23: Billing / dunning state machine
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestBillingService:

    def test_record_invoice_sets_grace_period(self, subscription, tenant):
        record = BillingService.record_invoice(
            tenant=tenant,
            amount_cents=9900,
            currency='USD',
            period_start=datetime.date.today(),
            period_end=datetime.date.today() + datetime.timedelta(days=30),
        )
        assert record.record_type == BillingRecord.TYPE_INVOICE
        assert record.status == BillingRecord.STATUS_PENDING
        subscription.refresh_from_db()
        assert subscription.grace_period_ends_at is not None

    def test_record_payment_clears_dunning(self, subscription, tenant):
        record = BillingService.record_invoice(
            tenant=tenant, amount_cents=9900, currency='USD',
            period_start=datetime.date.today(),
            period_end=datetime.date.today() + datetime.timedelta(days=30),
        )
        BillingService.record_payment(tenant=tenant, billing_record=record)
        record.refresh_from_db()
        assert record.status == BillingRecord.STATUS_PAID
        subscription.refresh_from_db()
        assert subscription.grace_period_ends_at is None
        assert subscription.status == TenantSubscription.STATUS_ACTIVE

    def test_apply_dunning_grace_to_read_only(self, subscription, tenant):
        # Set grace_period_ends_at to yesterday
        subscription.grace_period_ends_at = datetime.date.today() - datetime.timedelta(days=1)
        subscription.status = TenantSubscription.STATUS_ACTIVE
        subscription.save()
        BillingService.apply_dunning(tenant=tenant)
        subscription.refresh_from_db()
        assert subscription.status == TenantSubscription.STATUS_READ_ONLY

    def test_apply_dunning_read_only_to_suspended(self, subscription, tenant):
        # grace ended 8 days ago → past read-only window
        past = datetime.date.today() - datetime.timedelta(days=8)
        subscription.grace_period_ends_at = past
        subscription.status = TenantSubscription.STATUS_READ_ONLY
        subscription.save()
        BillingService.apply_dunning(tenant=tenant)
        subscription.refresh_from_db()
        tenant.refresh_from_db()
        assert subscription.status == TenantSubscription.STATUS_SUSPENDED
        assert tenant.status == Tenant.STATUS_SUSPENDED

    def test_apply_dunning_no_op_when_paid(self, subscription, tenant):
        # No grace period set → nothing changes
        BillingService.apply_dunning(tenant=tenant)
        subscription.refresh_from_db()
        assert subscription.status == TenantSubscription.STATUS_ACTIVE

    def test_is_read_only_true_when_read_only(self, subscription, tenant):
        subscription.status = TenantSubscription.STATUS_READ_ONLY
        subscription.save()
        assert BillingService.is_read_only(tenant=tenant) is True

    def test_is_read_only_false_when_active(self, subscription, tenant):
        assert BillingService.is_read_only(tenant=tenant) is False
