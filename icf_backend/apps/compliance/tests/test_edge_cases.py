"""
Tests for Phase 5 P1 edge cases (E-1 through E-5).
"""
import datetime

import pytest
from django.core.exceptions import ValidationError

from apps.common.edge_cases import (
    assert_as_of_not_regressed,
    assert_currency_consistent,
    assert_mailbox_active,
    assert_same_tenant,
)
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Firm A')


@pytest.fixture
def other_tenant(db):
    return Tenant.objects.create(firm_name='Firm B')


@pytest.fixture
def advisor(db, tenant):
    return CustomUser.objects.create_user(
        email='advisor@a.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='A', last_name='B',
    )


# ---------------------------------------------------------------------------
# E-1: Token expiry mid-campaign (BRU-05)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestE1TokenExpiry:

    def test_assert_mailbox_active_raises_when_suspended(self, tenant, advisor):
        from django.utils import timezone
        from apps.communications.models import MailboxConnection
        conn = MailboxConnection.objects.create(
            tenant=tenant, advisor=advisor,
            provider=MailboxConnection.PROVIDER_GMAIL,
            email_address='a@gmail.com',
            access_token_enc='enc',
            refresh_token_enc='enc',
            token_expires_at=timezone.now() + datetime.timedelta(hours=1),
            status=MailboxConnection.STATUS_SUSPENDED,
        )
        with pytest.raises(ValidationError, match='BRU-05'):
            assert_mailbox_active(conn)

    def test_assert_mailbox_active_raises_when_token_expired(self, tenant, advisor):
        from django.utils import timezone
        from apps.communications.models import MailboxConnection
        conn = MailboxConnection.objects.create(
            tenant=tenant, advisor=advisor,
            provider=MailboxConnection.PROVIDER_GMAIL,
            email_address='b@gmail.com',
            access_token_enc='enc',
            refresh_token_enc='enc',
            token_expires_at=timezone.now() - datetime.timedelta(minutes=5),
            status=MailboxConnection.STATUS_ACTIVE,
        )
        with pytest.raises(ValidationError, match='BRU-05'):
            assert_mailbox_active(conn)

    def test_assert_mailbox_active_passes_for_valid_connection(self, tenant, advisor):
        from django.utils import timezone
        from apps.communications.models import MailboxConnection
        conn = MailboxConnection.objects.create(
            tenant=tenant, advisor=advisor,
            provider=MailboxConnection.PROVIDER_GMAIL,
            email_address='c@gmail.com',
            access_token_enc='enc',
            refresh_token_enc='enc',
            token_expires_at=timezone.now() + datetime.timedelta(hours=6),
            status=MailboxConnection.STATUS_ACTIVE,
        )
        # Should not raise
        assert_mailbox_active(conn)

    def test_suspend_on_token_expiry_emits_event(self, tenant, advisor):
        """BRU-05: MailboxService.suspend_on_token_expiry sets status=suspended."""
        from django.utils import timezone
        from apps.communications.models import MailboxConnection
        from apps.communications.services import MailboxService
        conn = MailboxConnection.objects.create(
            tenant=tenant, advisor=advisor,
            provider=MailboxConnection.PROVIDER_GMAIL,
            email_address='d@gmail.com',
            access_token_enc='enc',
            refresh_token_enc='enc',
            token_expires_at=timezone.now() - datetime.timedelta(minutes=1),
            status=MailboxConnection.STATUS_ACTIVE,
        )
        MailboxService.suspend_on_token_expiry(connection=conn)
        conn.refresh_from_db()
        assert conn.status == MailboxConnection.STATUS_SUSPENDED


# ---------------------------------------------------------------------------
# E-2: Duplicate inbound race (BRU-16)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestE2DuplicateInbound:

    def test_process_inbound_idempotent(self, tenant, advisor):
        from django.utils import timezone
        from apps.communications.models import MailboxConnection
        from apps.communications.services import InboundMailService
        conn = MailboxConnection.objects.create(
            tenant=tenant, advisor=advisor,
            provider=MailboxConnection.PROVIDER_GMAIL,
            email_address='e@gmail.com',
            access_token_enc='enc',
            refresh_token_enc='enc',
            token_expires_at=timezone.now() + datetime.timedelta(hours=1),
            status=MailboxConnection.STATUS_ACTIVE,
        )
        c1 = InboundMailService.process_inbound_message(
            tenant=tenant, external_id='msg-dup-001',
            from_email='client@client.com', subject='Hello',
            body_ref='s3://body/1', connection=conn,
        )
        c2 = InboundMailService.process_inbound_message(
            tenant=tenant, external_id='msg-dup-001',
            from_email='client@client.com', subject='Hello',
            body_ref='s3://body/1', connection=conn,
        )
        # Same object returned — no duplicate created
        assert c1.pk == c2.pk
        from apps.communications.models import Communication
        count = Communication.objects.filter(external_id='msg-dup-001').count()
        assert count == 1

    def test_record_communication_idempotent(self, tenant, advisor):
        from apps.communications.services import CommunicationService
        c1 = CommunicationService.record_communication(
            tenant=tenant, channel='email', direction='outbound',
            body_ref='s3://b', external_id='out-dedup-001',
            sent_by=advisor,
        )
        c2 = CommunicationService.record_communication(
            tenant=tenant, channel='email', direction='outbound',
            body_ref='s3://b', external_id='out-dedup-001',
            sent_by=advisor,
        )
        assert c1.pk == c2.pk


# ---------------------------------------------------------------------------
# E-3: Stop-on-reply race (BRU-03)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestE3StopOnReplyRace:

    def test_stop_all_enrollments_is_idempotent(self, tenant, advisor):
        from apps.campaigns.models import Campaign, CampaignEnrollment
        from apps.campaigns.services import CampaignService
        from apps.leads.models import Lead

        campaign = Campaign.objects.create(
            tenant=tenant, name='Race Test', status=Campaign.STATUS_ACTIVE,
            created_by=advisor,
        )
        lead = Lead.objects.create(
            tenant=tenant, first_name='R', last_name='Test',
            email='r@test.com', status=Lead.STATUS_LEAD,
        )
        enrollment = CampaignEnrollment.objects.create(
            tenant=tenant, campaign=campaign, lead=lead,
            status=CampaignEnrollment.STATUS_ACTIVE,
        )
        # Stop once
        count1 = CampaignService.stop_all_enrollments_for_subject(
            tenant=tenant, lead=lead, reason='response',
        )
        assert count1 == 1
        # Stop again — already stopped, idempotent
        count2 = CampaignService.stop_all_enrollments_for_subject(
            tenant=tenant, lead=lead, reason='response',
        )
        assert count2 == 0
        enrollment.refresh_from_db()
        assert enrollment.status == CampaignEnrollment.STATUS_STOPPED

    def test_active_enrollment_blocks_duplicate_enroll(self, tenant, advisor):
        """BRU-03: an active enrollment cannot be duplicated for the same lead."""
        from apps.campaigns.models import Campaign, CampaignEnrollment
        from apps.leads.models import Lead
        campaign = Campaign.objects.create(
            tenant=tenant, name='Race Test 2', status=Campaign.STATUS_ACTIVE,
            created_by=advisor,
        )
        lead = Lead.objects.create(
            tenant=tenant, first_name='X', last_name='Y',
            email='x@y.com', status=Lead.STATUS_LEAD,
        )
        CampaignEnrollment.objects.create(
            tenant=tenant, campaign=campaign, lead=lead,
            status=CampaignEnrollment.STATUS_ACTIVE,
        )
        from django.core.exceptions import ValidationError as DjValidationError
        from apps.campaigns.services import CampaignService
        with pytest.raises(DjValidationError, match='BRU-03'):
            CampaignService.enroll_subject(
                campaign=campaign, actor=advisor, lead=lead,
            )


# ---------------------------------------------------------------------------
# E-4: Cross-tenant identity isolation (BRU-01)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestE4CrossTenantIsolation:

    def test_assert_same_tenant_passes(self, tenant, advisor):
        # advisor.tenant == tenant
        assert_same_tenant(advisor, tenant, 'advisor')

    def test_assert_same_tenant_raises_for_cross_tenant(self, tenant, other_tenant, advisor):
        with pytest.raises(ValidationError, match='BRU-01'):
            assert_same_tenant(advisor, other_tenant, 'advisor')

    def test_lead_cannot_be_accessed_from_other_tenant(self, tenant, other_tenant):
        from apps.leads.models import Lead
        lead = Lead.objects.create(
            tenant=tenant, first_name='A', last_name='B',
            email='a@b.com', status=Lead.STATUS_LEAD,
        )
        # BRU-01: querying from other tenant's perspective returns nothing
        cross = Lead.objects.filter(tenant=other_tenant, pk=lead.pk).first()
        assert cross is None

    def test_search_never_returns_other_tenant_results(self, tenant, other_tenant):
        from apps.leads.models import Lead
        from apps.search.services import GlobalSearchService
        # Create leads in other tenant with same name
        other_lead = Lead.objects.create(
            tenant=other_tenant, first_name='Unique', last_name='Name',
            email='unique@other.com', status=Lead.STATUS_LEAD,
        )
        user = CustomUser.objects.create_user(
            email='admin@a.com', password='pass',
            tenant=tenant, role=CustomUser.ROLE_TENANT_ADMIN,
            first_name='Ad', last_name='Min',
        )
        results = GlobalSearchService.search(tenant=tenant, user=user, query='Unique')
        ids = [(r.entity_type, r.entity_id) for r in results]
        assert ('lead', other_lead.pk) not in ids


# ---------------------------------------------------------------------------
# E-5: Currency / as-of integrity (BRU-26)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestE5CurrencyIntegrity:

    def test_assert_currency_consistent_passes_same(self):
        # Same currency → no error
        assert_currency_consistent('USD', 'USD', 'income')

    def test_assert_currency_consistent_raises_on_change(self):
        with pytest.raises(ValidationError, match='BRU-26'):
            assert_currency_consistent('USD', 'EUR', 'income')

    def test_assert_currency_consistent_passes_empty_existing(self):
        # No existing currency yet → allow any
        assert_currency_consistent('', 'USD', 'income')

    def test_assert_as_of_not_regressed_passes_forward(self):
        existing = datetime.date(2024, 1, 1)
        new = datetime.date(2024, 6, 1)
        assert_as_of_not_regressed(existing, new, 'income')

    def test_assert_as_of_not_regressed_raises_backward(self):
        existing = datetime.date(2024, 6, 1)
        new = datetime.date(2024, 1, 1)
        with pytest.raises(ValidationError, match='BRU-26'):
            assert_as_of_not_regressed(existing, new, 'income')

    def test_financial_service_blocks_silent_currency_change(self, tenant, advisor):
        """BRU-26: FinancialProfileService.update_profile raises on currency change."""
        from apps.leads.models import Lead
        from apps.financials.services import FinancialProfileService
        lead = Lead.objects.create(
            tenant=tenant, first_name='C', last_name='D',
            email='c@d.com', status=Lead.STATUS_CLIENT,
        )
        profile = FinancialProfileService.get_or_create_profile(
            tenant=tenant, lead=lead, actor=advisor,
        )
        # Set initial currency to USD
        profile.income_currency = 'USD'
        profile.save()
        # Try to silently change to EUR — must raise BRU-26
        with pytest.raises(ValidationError, match='BRU-26'):
            FinancialProfileService.update_profile(
                profile=profile, actor=advisor,
                income_currency='EUR',
            )

    def test_financial_service_blocks_backward_as_of(self, tenant, advisor):
        """BRU-26: update_profile raises if as_of_date moves backwards."""
        from apps.leads.models import Lead
        from apps.financials.services import FinancialProfileService
        lead = Lead.objects.create(
            tenant=tenant, first_name='E', last_name='F',
            email='e@f.com', status=Lead.STATUS_CLIENT,
        )
        profile = FinancialProfileService.get_or_create_profile(
            tenant=tenant, lead=lead, actor=advisor,
        )
        profile.income_as_of = datetime.date(2024, 6, 1)
        profile.save()
        with pytest.raises(ValidationError, match='BRU-26'):
            FinancialProfileService.update_profile(
                profile=profile, actor=advisor,
                income_as_of=datetime.date(2024, 1, 1),
            )
