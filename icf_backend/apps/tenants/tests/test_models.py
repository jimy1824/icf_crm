import pytest
from apps.tenants.models import Tenant, SubscriptionPlan, TenantSubscription
import datetime


@pytest.fixture
def plan(db):
    return SubscriptionPlan.objects.create(
        name='Starter', max_leads=100, max_users=5, max_storage_gb=10
    )


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Acme Advisors')


@pytest.mark.django_db
class TestTenant:
    def test_create(self, tenant):
        assert tenant.pk is not None
        assert tenant.status == Tenant.STATUS_ACTIVE
        assert tenant.timezone == 'America/New_York'

    def test_str(self, tenant):
        assert str(tenant) == 'Acme Advisors'

    def test_integer_pk(self, tenant):
        # Project uses Django default integer PKs (UUID PKs removed in base model refactor)
        assert isinstance(tenant.pk, int)
        assert tenant.pk > 0


@pytest.mark.django_db
class TestSubscriptionPlan:
    def test_create(self, plan):
        assert plan.is_active is True
        assert str(plan) == 'Starter'


@pytest.mark.django_db
class TestTenantSubscription:
    def test_create(self, tenant, plan):
        sub = TenantSubscription.objects.create(
            tenant=tenant, plan=plan, starts_at=datetime.date.today()
        )
        assert sub.status == TenantSubscription.STATUS_ACTIVE
        assert str(sub) == 'Acme Advisors — Starter'

    def test_one_subscription_per_tenant(self, tenant, plan):
        TenantSubscription.objects.create(
            tenant=tenant, plan=plan, starts_at=datetime.date.today()
        )
        with pytest.raises(Exception):
            TenantSubscription.objects.create(
                tenant=tenant, plan=plan, starts_at=datetime.date.today()
            )
