"""
Tests for BRU-36: Supervision / review workflow.
"""
import pytest
from django.core.exceptions import ValidationError

from apps.compliance.models import SupervisionReview, SupervisionRule
from apps.compliance.services import SupervisionService
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Supervised Firm')


@pytest.fixture
def advisor(db, tenant):
    return CustomUser.objects.create_user(
        email='advisor@firm.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Alice', last_name='A',
    )


@pytest.fixture
def supervisor(db, tenant):
    return CustomUser.objects.create_user(
        email='supervisor@firm.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_COMPLIANCE,
        first_name='Sam', last_name='S',
    )


@pytest.fixture
def rule(db, tenant, supervisor):
    return SupervisionRule.objects.create(
        tenant=tenant,
        channel='email',
        review_mode=SupervisionRule.REVIEW_MODE_POST,
        supervisor=supervisor,
    )


@pytest.fixture
def communication(db, tenant, advisor):
    from apps.communications.models import Communication
    return Communication.objects.create(
        tenant=tenant,
        channel=Communication.CHANNEL_EMAIL,
        direction=Communication.DIRECTION_OUTBOUND,
        status=Communication.STATUS_SENT,
        external_id='test-comm-001',
        subject='Investment Update',
        body_ref='s3://bucket/body',
        sent_by=advisor,
    )


@pytest.mark.django_db
class TestSupervisionRuleMatching:

    def test_get_applicable_rule_matches_email(self, tenant, advisor, rule):
        matched = SupervisionService.get_applicable_rule(
            tenant=tenant, advisor=advisor, channel='email',
        )
        assert matched == rule

    def test_get_applicable_rule_no_match_for_sms_when_rule_is_email(
        self, tenant, advisor, rule,
    ):
        matched = SupervisionService.get_applicable_rule(
            tenant=tenant, advisor=advisor, channel='sms',
        )
        assert matched is None

    def test_get_applicable_rule_all_channel_matches_any(self, tenant, advisor, supervisor):
        all_rule = SupervisionRule.objects.create(
            tenant=tenant, channel='all',
            review_mode=SupervisionRule.REVIEW_MODE_POST,
            supervisor=supervisor,
        )
        matched = SupervisionService.get_applicable_rule(
            tenant=tenant, advisor=advisor, channel='sms',
        )
        assert matched == all_rule

    def test_advisor_specific_rule_takes_priority(self, tenant, advisor, supervisor, rule):
        """Advisor-specific rule beats tenant-wide rule."""
        specific_rule = SupervisionRule.objects.create(
            tenant=tenant,
            applies_to_advisor=advisor,
            channel='email',
            review_mode=SupervisionRule.REVIEW_MODE_PRE,
            supervisor=supervisor,
        )
        matched = SupervisionService.get_applicable_rule(
            tenant=tenant, advisor=advisor, channel='email',
        )
        assert matched == specific_rule


@pytest.mark.django_db
class TestFlagForReview:

    def test_flag_creates_review(self, tenant, advisor, rule, communication):
        review = SupervisionService.flag_for_review(
            tenant=tenant, communication=communication, advisor=advisor,
        )
        assert review is not None
        assert review.status == SupervisionReview.STATUS_PENDING
        assert review.supervisor == rule.supervisor

    def test_flag_idempotent(self, tenant, advisor, rule, communication):
        r1 = SupervisionService.flag_for_review(
            tenant=tenant, communication=communication, advisor=advisor,
        )
        r2 = SupervisionService.flag_for_review(
            tenant=tenant, communication=communication, advisor=advisor,
        )
        assert r1.pk == r2.pk

    def test_no_rule_returns_none(self, tenant, advisor, communication):
        # No rule exists for this tenant → no review created
        review = SupervisionService.flag_for_review(
            tenant=tenant, communication=communication, advisor=advisor,
        )
        assert review is None


@pytest.mark.django_db
class TestApproveReject:

    def test_approve_pending_review(self, tenant, advisor, supervisor, rule, communication):
        review = SupervisionService.flag_for_review(
            tenant=tenant, communication=communication, advisor=advisor,
        )
        review = SupervisionService.approve(
            review=review, reviewer=supervisor, notes='Looks good.',
        )
        assert review.status == SupervisionReview.STATUS_APPROVED
        assert review.reviewed_by == supervisor
        assert review.review_notes == 'Looks good.'
        assert review.reviewed_at is not None

    def test_reject_pending_review(self, tenant, advisor, supervisor, rule, communication):
        review = SupervisionService.flag_for_review(
            tenant=tenant, communication=communication, advisor=advisor,
        )
        review = SupervisionService.reject(
            review=review, reviewer=supervisor, notes='Policy violation.',
        )
        assert review.status == SupervisionReview.STATUS_REJECTED

    def test_cannot_approve_already_approved(self, tenant, advisor, supervisor, rule, communication):
        review = SupervisionService.flag_for_review(
            tenant=tenant, communication=communication, advisor=advisor,
        )
        SupervisionService.approve(review=review, reviewer=supervisor)
        review.refresh_from_db()
        with pytest.raises(ValidationError, match='already'):
            SupervisionService.approve(review=review, reviewer=supervisor)

    def test_cannot_reject_already_rejected(self, tenant, advisor, supervisor, rule, communication):
        review = SupervisionService.flag_for_review(
            tenant=tenant, communication=communication, advisor=advisor,
        )
        SupervisionService.reject(review=review, reviewer=supervisor, notes='No.')
        review.refresh_from_db()
        with pytest.raises(ValidationError, match='already'):
            SupervisionService.reject(review=review, reviewer=supervisor, notes='Again.')

    def test_escalate(self, tenant, advisor, supervisor, rule, communication):
        review = SupervisionService.flag_for_review(
            tenant=tenant, communication=communication, advisor=advisor,
        )
        review = SupervisionService.escalate(review=review, reviewer=supervisor)
        assert review.status == SupervisionReview.STATUS_ESCALATED

    def test_cannot_escalate_rejected(self, tenant, advisor, supervisor, rule, communication):
        review = SupervisionService.flag_for_review(
            tenant=tenant, communication=communication, advisor=advisor,
        )
        SupervisionService.reject(review=review, reviewer=supervisor, notes='No.')
        review.refresh_from_db()
        with pytest.raises(ValidationError):
            SupervisionService.escalate(review=review, reviewer=supervisor)


@pytest.mark.django_db
class TestPreSendHold:

    def test_pre_send_review_holds_communication(self, tenant, advisor, supervisor):
        pre_rule = SupervisionRule.objects.create(
            tenant=tenant, channel='email',
            review_mode=SupervisionRule.REVIEW_MODE_PRE,
            supervisor=supervisor,
        )
        from apps.communications.models import Communication
        comm = Communication.objects.create(
            tenant=tenant,
            channel=Communication.CHANNEL_EMAIL,
            direction=Communication.DIRECTION_OUTBOUND,
            status=Communication.STATUS_QUEUED,
            external_id='pre-send-001',
            body_ref='s3://bucket/body',
            sent_by=advisor,
        )
        SupervisionService.flag_for_review(
            tenant=tenant, communication=comm, advisor=advisor,
        )
        assert SupervisionService.is_held_pending_review(communication=comm) is True

    def test_post_send_review_does_not_hold(self, tenant, advisor, supervisor, rule, communication):
        SupervisionService.flag_for_review(
            tenant=tenant, communication=communication, advisor=advisor,
        )
        assert SupervisionService.is_held_pending_review(communication=communication) is False

    def test_approved_pre_send_releases_hold(self, tenant, advisor, supervisor):
        pre_rule = SupervisionRule.objects.create(
            tenant=tenant, channel='email',
            review_mode=SupervisionRule.REVIEW_MODE_PRE,
            supervisor=supervisor,
        )
        from apps.communications.models import Communication
        comm = Communication.objects.create(
            tenant=tenant,
            channel=Communication.CHANNEL_EMAIL,
            direction=Communication.DIRECTION_OUTBOUND,
            status=Communication.STATUS_QUEUED,
            external_id='pre-send-002',
            body_ref='s3://bucket/body',
            sent_by=advisor,
        )
        review = SupervisionService.flag_for_review(
            tenant=tenant, communication=comm, advisor=advisor,
        )
        SupervisionService.approve(review=review, reviewer=supervisor)
        assert SupervisionService.is_held_pending_review(communication=comm) is False
