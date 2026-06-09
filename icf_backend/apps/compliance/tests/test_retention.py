"""
Tests for BRU-37 (retention) and BRU-38 (legal holds).
"""
import datetime

import pytest
from django.core.exceptions import ValidationError

from apps.compliance.models import RetentionPolicy, RetentionRecord
from apps.compliance.services import LegalHoldService, RetentionService
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm')


@pytest.fixture
def actor(db, tenant):
    return CustomUser.objects.create_user(
        email='co@firm.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_COMPLIANCE,
        first_name='C', last_name='O',
    )


# ---------------------------------------------------------------------------
# BRU-37: Retention registration and enforcement
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestRetentionService:

    def test_register_creates_record(self, tenant, actor):
        record = RetentionService.register(
            tenant=tenant, entity_type='Communication', entity_id=42,
        )
        assert record.pk is not None
        assert record.entity_type == 'Communication'
        assert record.entity_id == '42'
        assert record.retained_until > datetime.date.today()

    def test_register_idempotent(self, tenant):
        r1 = RetentionService.register(
            tenant=tenant, entity_type='Communication', entity_id=99,
        )
        r2 = RetentionService.register(
            tenant=tenant, entity_type='Communication', entity_id=99,
        )
        assert r1.pk == r2.pk

    def test_register_never_shortens_window(self, tenant):
        # First register with 7 years
        r1 = RetentionService.register(
            tenant=tenant, entity_type='Document', entity_id=1,
            retention_years=7,
        )
        original_until = r1.retained_until
        # Second call with only 1 year — must NOT shorten
        r2 = RetentionService.register(
            tenant=tenant, entity_type='Document', entity_id=1,
            retention_years=1,
        )
        assert r2.retained_until == original_until

    def test_register_extends_window(self, tenant):
        r1 = RetentionService.register(
            tenant=tenant, entity_type='Document', entity_id=2,
            retention_years=2,
        )
        r2 = RetentionService.register(
            tenant=tenant, entity_type='Document', entity_id=2,
            retention_years=10,
        )
        assert r2.retained_until > r1.retained_until

    def test_is_deletable_false_within_window(self, tenant):
        RetentionService.register(
            tenant=tenant, entity_type='Communication', entity_id=5,
            retention_years=7,
        )
        assert RetentionService.is_deletable(
            tenant=tenant, entity_type='Communication', entity_id=5,
        ) is False

    def test_is_deletable_true_when_no_record(self, tenant):
        assert RetentionService.is_deletable(
            tenant=tenant, entity_type='Communication', entity_id=99999,
        ) is True

    def test_is_deletable_true_after_window(self, tenant):
        record = RetentionService.register(
            tenant=tenant, entity_type='Communication', entity_id=6,
            retention_years=1,
        )
        # Manually backdate to simulate expiry
        record.retained_until = datetime.date.today() - datetime.timedelta(days=1)
        record.save()
        assert RetentionService.is_deletable(
            tenant=tenant, entity_type='Communication', entity_id=6,
        ) is True

    def test_assert_deletable_raises_within_window(self, tenant):
        RetentionService.register(
            tenant=tenant, entity_type='AuditEvent', entity_id=7,
            retention_years=7,
        )
        with pytest.raises(ValidationError, match='BRU-37'):
            RetentionService.assert_deletable(
                tenant=tenant, entity_type='AuditEvent', entity_id=7,
            )

    def test_configure_policy(self, tenant, actor):
        policy = RetentionService.configure_policy(
            tenant=tenant, entity_type='communication',
            retention_years=10, actor=actor,
        )
        assert policy.retention_years == 10

    def test_register_uses_policy(self, tenant, actor):
        RetentionService.configure_policy(
            tenant=tenant, entity_type='communication',
            retention_years=10, actor=actor,
        )
        record = RetentionService.register(
            tenant=tenant, entity_type='communication', entity_id=100,
        )
        # Should be ~10 years, not the default 7
        expected_min = datetime.date.today() + datetime.timedelta(days=9 * 365)
        assert record.retained_until >= expected_min

    def test_approve_deletion_raises_within_window(self, tenant, actor):
        RetentionService.register(
            tenant=tenant, entity_type='Communication', entity_id=8,
            retention_years=7,
        )
        with pytest.raises(ValidationError, match='BRU-37'):
            RetentionService.approve_deletion(
                tenant=tenant, entity_type='Communication', entity_id=8, actor=actor,
            )

    def test_approve_deletion_succeeds_after_window(self, tenant, actor):
        record = RetentionService.register(
            tenant=tenant, entity_type='Communication', entity_id=9,
            retention_years=1,
        )
        record.retained_until = datetime.date.today() - datetime.timedelta(days=1)
        record.save()
        record = RetentionService.approve_deletion(
            tenant=tenant, entity_type='Communication', entity_id=9, actor=actor,
        )
        assert record.cleared_for_deletion_at is not None


# ---------------------------------------------------------------------------
# BRU-38: Legal hold overrides deletion
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLegalHoldService:

    def test_place_hold_creates_record(self, tenant, actor):
        record = LegalHoldService.place_hold(
            tenant=tenant, entity_type='Communication', entity_id=10,
            actor=actor, reason='Regulatory investigation',
        )
        assert record.is_under_legal_hold is True
        assert record.hold_reason == 'Regulatory investigation'

    def test_bru38_hold_blocks_deletion_even_after_window(self, tenant, actor):
        record = LegalHoldService.place_hold(
            tenant=tenant, entity_type='Communication', entity_id=11,
            actor=actor, reason='Litigation hold',
        )
        # Expire the retention window
        record.retained_until = datetime.date.today() - datetime.timedelta(days=1)
        record.save()
        # BRU-38: still not deletable
        assert RetentionService.is_deletable(
            tenant=tenant, entity_type='Communication', entity_id=11,
        ) is False

    def test_lift_hold_allows_deletion_after_window(self, tenant, actor):
        record = LegalHoldService.place_hold(
            tenant=tenant, entity_type='Communication', entity_id=12,
            actor=actor, reason='Temp hold',
        )
        record.retained_until = datetime.date.today() - datetime.timedelta(days=1)
        record.save()
        LegalHoldService.lift_hold(
            tenant=tenant, entity_type='Communication', entity_id=12,
            actor=actor, reason='Investigation closed',
        )
        assert RetentionService.is_deletable(
            tenant=tenant, entity_type='Communication', entity_id=12,
        ) is True

    def test_lift_hold_still_blocks_if_window_active(self, tenant, actor):
        LegalHoldService.place_hold(
            tenant=tenant, entity_type='Communication', entity_id=13,
            actor=actor, reason='Hold',
        )
        LegalHoldService.lift_hold(
            tenant=tenant, entity_type='Communication', entity_id=13,
            actor=actor,
        )
        # Window is still active (7 years default) → not deletable
        assert RetentionService.is_deletable(
            tenant=tenant, entity_type='Communication', entity_id=13,
        ) is False

    def test_lift_nonexistent_hold_raises(self, tenant, actor):
        with pytest.raises(ValidationError):
            LegalHoldService.lift_hold(
                tenant=tenant, entity_type='Communication', entity_id=99999,
                actor=actor,
            )
