import pytest
from apps.leads.models import Lead, KanbanCard
from apps.tenants.models import Tenant


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm')


@pytest.fixture
def lead(tenant):
    return Lead.objects.create(
        tenant=tenant,
        first_name='Alice',
        last_name='Walker',
        email='alice@example.com',
        source=Lead.SOURCE_MANUAL,
    )


@pytest.mark.django_db
class TestLead:
    def test_create(self, lead):
        assert lead.pk is not None
        assert lead.status == Lead.STATUS_LEAD
        assert lead.opted_out is False
        assert lead.is_suppressed is False

    def test_str(self, lead):
        assert 'Alice' in str(lead)
        assert 'alice@example.com' in str(lead)

    def test_unique_email_per_tenant(self, tenant):
        Lead.objects.create(
            tenant=tenant, first_name='A', last_name='B',
            email='dup@test.com', source=Lead.SOURCE_MANUAL,
        )
        with pytest.raises(Exception):
            Lead.objects.create(
                tenant=tenant, first_name='C', last_name='D',
                email='dup@test.com', source=Lead.SOURCE_MANUAL,
            )

    def test_same_email_different_tenants_allowed(self, db):
        t1 = Tenant.objects.create(firm_name='Firm 1')
        t2 = Tenant.objects.create(firm_name='Firm 2')
        Lead.objects.create(
            tenant=t1, first_name='A', last_name='B',
            email='shared@test.com', source=Lead.SOURCE_MANUAL,
        )
        lead2 = Lead.objects.create(
            tenant=t2, first_name='C', last_name='D',
            email='shared@test.com', source=Lead.SOURCE_MANUAL,
        )
        assert lead2.pk is not None


@pytest.mark.django_db
class TestKanbanCard:
    def test_create(self, lead):
        card = KanbanCard.objects.create(lead=lead, stage='new', position=0)
        assert card.pk is not None
        assert str(lead.first_name) in str(card)
