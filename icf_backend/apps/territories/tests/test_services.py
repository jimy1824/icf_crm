"""
Territory service tests — BRU-01 isolation, soft-delete, advisor assignment,
round-robin distribution, no-advisor notification, analytics.
"""
import pytest
from django.core.exceptions import ValidationError

from apps.territories.models import Territory, AdvisorTerritory
from apps.territories.services import TerritoryService, TerritoryAnalyticsService
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm')


@pytest.fixture
def other_tenant(db):
    return Tenant.objects.create(firm_name='Other Firm')


@pytest.fixture
def admin(db, tenant):
    return CustomUser.objects.create_user(
        email='admin@firm.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_TENANT_ADMIN,
        first_name='Admin', last_name='User',
    )


@pytest.fixture
def advisor(db, tenant):
    return CustomUser.objects.create_user(
        email='advisor@firm.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Alice', last_name='Advisor',
    )


@pytest.fixture
def advisor2(db, tenant):
    return CustomUser.objects.create_user(
        email='advisor2@firm.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Bob', last_name='Advisor',
    )


@pytest.fixture
def territory(db, tenant, admin):
    return TerritoryService.create_territory(
        tenant=tenant, name='West Houston', actor=admin,
    )


@pytest.mark.django_db
class TestCreateTerritory:

    def test_create_returns_territory(self, tenant, admin):
        t = TerritoryService.create_territory(tenant=tenant, name='East Houston', actor=admin)
        assert t.pk is not None
        assert t.name == 'East Houston'
        assert t.is_active is True
        assert t.tenant == tenant

    def test_name_unique_per_tenant(self, tenant, territory, admin):
        with pytest.raises(ValidationError):
            TerritoryService.create_territory(tenant=tenant, name='West Houston', actor=admin)

    def test_bru01_same_name_different_tenants_allowed(self, tenant, other_tenant, territory, admin):
        other_admin = CustomUser.objects.create_user(
            email='admin@other.com', password='pass', tenant=other_tenant,
            role=CustomUser.ROLE_TENANT_ADMIN, first_name='X', last_name='Y',
        )
        t2 = TerritoryService.create_territory(
            tenant=other_tenant, name='West Houston', actor=other_admin,
        )
        assert t2.pk != territory.pk


@pytest.mark.django_db
class TestSoftDelete:

    def test_deactivate_sets_is_active_false(self, territory, admin):
        TerritoryService.deactivate_territory(territory=territory, actor=admin)
        territory.refresh_from_db()
        assert territory.is_active is False

    def test_deactivate_idempotent(self, territory, admin):
        TerritoryService.deactivate_territory(territory=territory, actor=admin)
        TerritoryService.deactivate_territory(territory=territory, actor=admin)
        territory.refresh_from_db()
        assert territory.is_active is False

    def test_leads_preserved_after_deactivation(self, tenant, territory, admin):
        from apps.leads.models import Lead
        lead = Lead.objects.create(
            tenant=tenant, first_name='J', last_name='D', email='j@d.com',
            status=Lead.STATUS_LEAD, territory=territory,
        )
        TerritoryService.deactivate_territory(territory=territory, actor=admin)
        lead.refresh_from_db()
        assert lead.territory_id == territory.pk


@pytest.mark.django_db
class TestAdvisorAssignment:

    def test_assign_advisor(self, territory, advisor, admin):
        at = TerritoryService.assign_advisor(territory=territory, advisor=advisor, actor=admin)
        assert at.pk is not None
        assert at.advisor == advisor
        assert at.territory == territory

    def test_assign_idempotent(self, territory, advisor, admin):
        at1 = TerritoryService.assign_advisor(territory=territory, advisor=advisor, actor=admin)
        at2 = TerritoryService.assign_advisor(territory=territory, advisor=advisor, actor=admin)
        assert at1.pk == at2.pk

    def test_bru01_cross_tenant_blocked(self, territory, other_tenant, admin):
        cross_advisor = CustomUser.objects.create_user(
            email='x@other.com', password='pass', tenant=other_tenant,
            role=CustomUser.ROLE_ADVISOR, first_name='X', last_name='X',
        )
        with pytest.raises(ValidationError, match='BRU-01'):
            TerritoryService.assign_advisor(territory=territory, advisor=cross_advisor, actor=admin)

    def test_inactive_territory_blocks_assignment(self, territory, advisor, admin):
        TerritoryService.deactivate_territory(territory=territory, actor=admin)
        with pytest.raises(ValidationError):
            TerritoryService.assign_advisor(territory=territory, advisor=advisor, actor=admin)

    def test_non_advisor_role_blocked(self, territory, admin):
        with pytest.raises(ValidationError):
            TerritoryService.assign_advisor(territory=territory, advisor=admin, actor=admin)

    def test_remove_advisor(self, territory, advisor, admin):
        TerritoryService.assign_advisor(territory=territory, advisor=advisor, actor=admin)
        TerritoryService.remove_advisor(territory=territory, advisor=advisor, actor=admin)
        assert not AdvisorTerritory.objects.filter(advisor=advisor, territory=territory).exists()

    def test_remove_nonexistent_is_safe(self, territory, advisor, admin):
        TerritoryService.remove_advisor(territory=territory, advisor=advisor, actor=admin)


@pytest.mark.django_db
class TestLeadDistribution:

    def test_distribute_assigns_advisor(self, tenant, territory, advisor, admin):
        from apps.leads.models import Lead
        TerritoryService.assign_advisor(territory=territory, advisor=advisor, actor=admin)
        lead = Lead.objects.create(
            tenant=tenant, first_name='L', last_name='D', email='l@d.com',
            status=Lead.STATUS_LEAD, territory=territory,
        )
        TerritoryService.distribute_lead(lead=lead)
        lead.refresh_from_db()
        assert lead.assigned_advisors.filter(pk=advisor.pk).exists()

    def test_round_robin_balances_across_two_advisors(self, tenant, territory, advisor, advisor2, admin):
        """First lead → advisor with fewer leads (advisor2 = 0 when advisor has 1)."""
        from apps.leads.models import Lead
        TerritoryService.assign_advisor(territory=territory, advisor=advisor, actor=admin)
        TerritoryService.assign_advisor(territory=territory, advisor=advisor2, actor=admin)

        lead1 = Lead.objects.create(
            tenant=tenant, first_name='L1', last_name='D', email='l1@d.com',
            status=Lead.STATUS_LEAD, territory=territory,
        )
        TerritoryService.distribute_lead(lead=lead1)
        lead1.refresh_from_db()

        lead2 = Lead.objects.create(
            tenant=tenant, first_name='L2', last_name='D', email='l2@d.com',
            status=Lead.STATUS_LEAD, territory=territory,
        )
        TerritoryService.distribute_lead(lead=lead2)
        lead2.refresh_from_db()

        assigned1 = lead1.assigned_advisors.first()
        assigned2 = lead2.assigned_advisors.first()
        # Both advisors should each get one lead
        assert assigned1 != assigned2

    def test_no_advisor_sends_notification(self, tenant, territory, admin):
        """No active advisor → Tenant Admin receives in-app notification."""
        from apps.leads.models import Lead
        from apps.notifications.models import Notification
        lead = Lead.objects.create(
            tenant=tenant, first_name='N', last_name='A', email='na@d.com',
            status=Lead.STATUS_LEAD, territory=territory,
        )
        TerritoryService.distribute_lead(lead=lead)
        # Lead stays unassigned
        lead.refresh_from_db()
        assert lead.assigned_advisors.count() == 0
        # Admin notification created
        assert Notification.objects.filter(
            tenant=tenant, recipient=admin, event_type='territory.no_advisor',
        ).exists()

    def test_no_territory_is_noop(self, tenant, admin):
        from apps.leads.models import Lead
        lead = Lead.objects.create(
            tenant=tenant, first_name='X', last_name='Y', email='x@y.com',
            status=Lead.STATUS_LEAD,
        )
        TerritoryService.distribute_lead(lead=lead)
        # No exception; no assignment
        lead.refresh_from_db()
        assert lead.assigned_advisors.count() == 0


@pytest.mark.django_db
class TestResolveOrWarn:

    def test_resolves_case_insensitive(self, tenant, territory):
        found = TerritoryService.resolve_or_warn(tenant=tenant, territory_name='west houston')
        assert found == territory

    def test_returns_none_for_unknown(self, tenant):
        found = TerritoryService.resolve_or_warn(tenant=tenant, territory_name='Unknown Region')
        assert found is None

    def test_empty_name_returns_none(self, tenant):
        found = TerritoryService.resolve_or_warn(tenant=tenant, territory_name='')
        assert found is None

    def test_bru01_inactive_territory_not_resolved(self, tenant, territory, admin):
        TerritoryService.deactivate_territory(territory=territory, actor=admin)
        found = TerritoryService.resolve_or_warn(tenant=tenant, territory_name='West Houston')
        assert found is None


@pytest.mark.django_db
class TestLeadCreateWithTerritory:

    def test_create_lead_with_territory_name(self, tenant, territory, admin):
        from apps.leads.services import LeadService
        lead = LeadService.create_lead(
            tenant=tenant, first_name='J', last_name='D', email='jd@test.com',
            territory_name='West Houston', actor=admin,
        )
        assert lead.territory == territory

    def test_create_lead_with_unknown_territory_name(self, tenant, admin):
        from apps.leads.services import LeadService
        lead = LeadService.create_lead(
            tenant=tenant, first_name='J', last_name='D', email='jd2@test.com',
            territory_name='Atlantis', actor=admin,
        )
        assert lead.territory is None

    def test_create_lead_without_territory_name(self, tenant, admin):
        from apps.leads.services import LeadService
        lead = LeadService.create_lead(
            tenant=tenant, first_name='J', last_name='D', email='jd3@test.com',
            actor=admin,
        )
        assert lead.territory is None


@pytest.mark.django_db
class TestTerritoryAnalytics:

    def test_territory_summary_counts(self, tenant, territory, advisor, admin):
        from apps.leads.models import Lead
        TerritoryService.assign_advisor(territory=territory, advisor=advisor, actor=admin)

        Lead.objects.create(
            tenant=tenant, first_name='A', last_name='B', email='a@b.com',
            status=Lead.STATUS_LEAD, territory=territory,
        )
        summary = TerritoryAnalyticsService.territory_summary(
            tenant=tenant, territory=territory,
        )
        assert summary['total_leads'] == 1
        assert summary['active_advisors'] == 1
        assert summary['territory'] == 'West Houston'

    def test_graph_leads_per_territory(self, tenant, territory, admin):
        from apps.leads.models import Lead
        Lead.objects.create(
            tenant=tenant, first_name='A', last_name='B', email='a@b.com',
            status=Lead.STATUS_LEAD, territory=territory,
        )
        Lead.objects.create(
            tenant=tenant, first_name='C', last_name='D', email='c@d.com',
            status=Lead.STATUS_LEAD, territory=territory,
        )
        rows = TerritoryAnalyticsService.graph_leads_per_territory(tenant=tenant)
        assert len(rows) == 1
        assert rows[0]['value'] == 2

    def test_graph_advisors_per_territory(self, tenant, territory, advisor, advisor2, admin):
        TerritoryService.assign_advisor(territory=territory, advisor=advisor, actor=admin)
        TerritoryService.assign_advisor(territory=territory, advisor=advisor2, actor=admin)
        rows = TerritoryAnalyticsService.graph_advisors_per_territory(tenant=tenant)
        assert rows[0]['value'] == 2

    def test_bru01_graph_does_not_cross_tenants(self, tenant, other_tenant):
        other_admin = CustomUser.objects.create_user(
            email='adm@other.com', password='pass', tenant=other_tenant,
            role=CustomUser.ROLE_TENANT_ADMIN, first_name='X', last_name='Y',
        )
        other_territory = TerritoryService.create_territory(
            tenant=other_tenant, name='Dallas', actor=other_admin,
        )
        from apps.leads.models import Lead
        Lead.objects.create(
            tenant=other_tenant, first_name='A', last_name='B', email='a@other.com',
            status=Lead.STATUS_LEAD, territory=other_territory,
        )
        rows = TerritoryAnalyticsService.graph_leads_per_territory(tenant=tenant)
        # Our tenant has no territory-leads — empty or only own data
        for row in rows:
            assert row['territory'] != 'Dallas'

    def test_advisor_territory_analytics(self, tenant, territory, advisor, admin):
        from apps.leads.models import Lead
        TerritoryService.assign_advisor(territory=territory, advisor=advisor, actor=admin)
        Lead.objects.create(
            tenant=tenant, first_name='A', last_name='B', email='a@x.com',
            status=Lead.STATUS_LEAD, territory=territory,
        )
        lead = Lead.objects.get(email='a@x.com')
        lead.assigned_advisors.add(advisor)

        result = TerritoryAnalyticsService.advisor_territory_analytics(
            tenant=tenant, advisor=advisor,
        )
        assert result['advisor_id'] == advisor.pk
        assert len(result['territories']) == 1
        assert result['territories'][0]['leads_count'] == 1
