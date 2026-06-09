import pytest
from django.core.exceptions import ValidationError

from apps.leads.models import Lead, KanbanCard, ActivityNote
from apps.leads.services import LeadService
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Acme Advisors')


@pytest.fixture
def advisor(tenant):
    return CustomUser.objects.create_user(
        email='advisor@acme.com',
        password='pass1234!',
        first_name='Jane',
        last_name='Advisor',
        role=CustomUser.ROLE_ADVISOR,
        tenant=tenant,
    )


@pytest.fixture
def lead(tenant):
    return Lead.objects.create(
        tenant=tenant,
        first_name='Alice',
        last_name='Test',
        email='alice@test.com',
        source=Lead.SOURCE_MANUAL,
        pipeline_stage=Lead.STAGE_NEW,
        status=Lead.STATUS_LEAD,
    )


@pytest.mark.django_db
class TestLeadServiceCreate:

    def test_creates_lead_with_kanban_card(self, tenant, advisor):
        """LeadService.create_lead must create both Lead and KanbanCard atomically."""
        lead = LeadService.create_lead(
            tenant=tenant,
            first_name='Bob',
            last_name='Smith',
            email='bob@test.com',
            actor=advisor,
        )
        assert lead.pk is not None
        assert lead.status == Lead.STATUS_LEAD
        assert lead.pipeline_stage == Lead.STAGE_NEW
        assert KanbanCard.objects.filter(lead=lead).exists()

    def test_creates_system_timeline_entry(self, tenant, advisor):
        """A system note must be written on creation (BRU-12)."""
        lead = LeadService.create_lead(
            tenant=tenant,
            first_name='Carol',
            last_name='Test',
            email='carol@test.com',
            actor=advisor,
        )
        note = ActivityNote.objects.filter(lead=lead, activity_type=ActivityNote.TYPE_SYSTEM).first()
        assert note is not None
        assert note.is_private is True

    def test_idempotent_on_duplicate_email(self, tenant, advisor):
        """BRU-16: creating with the same tenant+email must return the existing lead, not error."""
        lead1 = LeadService.create_lead(
            tenant=tenant, first_name='A', last_name='B',
            email='dup@test.com', actor=advisor,
        )
        lead2 = LeadService.create_lead(
            tenant=tenant, first_name='X', last_name='Y',
            email='dup@test.com', actor=advisor,
        )
        assert lead1.pk == lead2.pk
        assert Lead.objects.filter(tenant=tenant, email='dup@test.com').count() == 1

    def test_different_tenants_same_email_allowed(self, db, advisor):
        """BRU-01: same email in two different tenants must not collide."""
        t1 = Tenant.objects.create(firm_name='Firm A')
        t2 = Tenant.objects.create(firm_name='Firm B')
        l1 = LeadService.create_lead(tenant=t1, first_name='A', last_name='B', email='x@test.com')
        l2 = LeadService.create_lead(tenant=t2, first_name='C', last_name='D', email='x@test.com')
        assert l1.pk != l2.pk


@pytest.mark.django_db
class TestLeadServiceAssign:

    def test_assign_advisor(self, tenant, lead, advisor):
        """BRU-06: lead must be assignable to at least one advisor."""
        LeadService.assign_advisors(lead=lead, advisor_ids=[advisor.pk], actor=advisor)
        assert advisor in lead.assigned_advisors.all()

    def test_assign_writes_timeline_and_audit(self, tenant, lead, advisor):
        """BRU-12 / BRU-33: assigning must write a system note and audit entry."""
        from apps.audit.models import AuditEvent
        LeadService.assign_advisors(lead=lead, advisor_ids=[advisor.pk], actor=advisor)
        assert ActivityNote.objects.filter(lead=lead, activity_type=ActivityNote.TYPE_SYSTEM).exists()
        assert AuditEvent.objects.filter(entity_type='Lead', action='lead.assign').exists()

    def test_assign_invalid_advisor_raises(self, tenant, lead):
        """BRU-06: assigning a non-existent or wrong-tenant advisor must raise."""
        with pytest.raises(ValidationError):
            LeadService.assign_advisors(lead=lead, advisor_ids=[99999])

    def test_assign_wrong_role_raises(self, tenant, lead):
        """BRU-06: only advisor/team_lead roles can be assigned."""
        admin = CustomUser.objects.create_user(
            email='admin@acme.com', password='pass1234!',
            first_name='Admin', last_name='User',
            role=CustomUser.ROLE_TENANT_ADMIN, tenant=tenant,
        )
        with pytest.raises(ValidationError):
            LeadService.assign_advisors(lead=lead, advisor_ids=[admin.pk])


@pytest.mark.django_db
class TestLeadServiceMoveStage:

    def test_move_stage_updates_lead_and_card(self, tenant, lead, advisor):
        """BRU-31: stage move must update lead.pipeline_stage, lead.status, and kanban card atomically."""
        KanbanCard.objects.create(lead=lead, stage=Lead.STAGE_NEW, position=0)
        LeadService.move_stage(lead=lead, new_stage=Lead.STAGE_CONTACTED, actor=advisor)
        lead.refresh_from_db()
        assert lead.pipeline_stage == Lead.STAGE_CONTACTED
        assert lead.status == Lead.STAGE_TO_STATUS[Lead.STAGE_CONTACTED]
        assert lead.kanban_card.stage == Lead.STAGE_CONTACTED

    def test_move_stage_writes_timeline_entry(self, tenant, lead, advisor):
        """BRU-31 / BRU-12: stage move must write a STAGE_CHANGE timeline entry."""
        KanbanCard.objects.create(lead=lead, stage=Lead.STAGE_NEW, position=0)
        LeadService.move_stage(lead=lead, new_stage=Lead.STAGE_QUALIFIED, actor=advisor)
        note = ActivityNote.objects.filter(
            lead=lead, activity_type=ActivityNote.TYPE_STAGE_CHANGE
        ).first()
        assert note is not None
        assert 'qualified' in note.body

    def test_move_stage_writes_audit_entry(self, tenant, lead, advisor):
        """BRU-33: audit entry must be written on stage move."""
        from apps.audit.models import AuditEvent
        KanbanCard.objects.create(lead=lead, stage=Lead.STAGE_NEW, position=0)
        LeadService.move_stage(lead=lead, new_stage=Lead.STAGE_QUALIFIED, actor=advisor)
        assert AuditEvent.objects.filter(
            action='lead.stage_change', entity_type='Lead',
        ).exists()

    def test_closed_won_sets_converted_status(self, tenant, lead, advisor):
        """STAGE_CLOSED_WON must set status=converted (BRU-31, STAGE_TO_STATUS mapping)."""
        KanbanCard.objects.create(lead=lead, stage=Lead.STAGE_NEW, position=0)
        LeadService.move_stage(lead=lead, new_stage=Lead.STAGE_CLOSED_WON, actor=advisor)
        lead.refresh_from_db()
        assert lead.status == Lead.STATUS_CLIENT

    def test_closed_lost_sets_lost_status(self, tenant, lead, advisor):
        KanbanCard.objects.create(lead=lead, stage=Lead.STAGE_NEW, position=0)
        LeadService.move_stage(lead=lead, new_stage=Lead.STAGE_CLOSED_LOST, actor=advisor)
        lead.refresh_from_db()
        assert lead.status == Lead.STATUS_LOST

    def test_invalid_stage_raises(self, tenant, lead, advisor):
        with pytest.raises(ValidationError):
            LeadService.move_stage(lead=lead, new_stage='invalid_stage', actor=advisor)


@pytest.mark.django_db
class TestLeadServiceNotes:

    def test_add_private_note(self, tenant, lead, advisor):
        """BRU-08 / BRU-12: private note written to timeline."""
        note = LeadService.add_note(
            tenant=tenant, lead=lead, author=advisor,
            body='Internal advisor note.', is_private=True,
        )
        assert note.is_private is True
        assert note.lead == lead

    def test_add_client_visible_note(self, tenant, lead, advisor):
        note = LeadService.add_note(
            tenant=tenant, lead=lead, author=advisor,
            body='Shared with client.', is_private=False,
        )
        assert note.is_private is False

    def test_add_note_writes_audit(self, tenant, lead, advisor):
        """BRU-33: adding a note must write an audit entry."""
        from apps.audit.models import AuditEvent
        LeadService.add_note(
            tenant=tenant, lead=lead, author=advisor,
            body='Test.', is_private=True,
        )
        assert AuditEvent.objects.filter(action='timeline.note_added').exists()


@pytest.mark.django_db
class TestOptOut:

    def test_opt_out_sets_flag(self, tenant, lead, advisor):
        """BRU-07: opt-out must set opted_out=True."""
        LeadService.opt_out(lead=lead, actor=advisor)
        lead.refresh_from_db()
        assert lead.opted_out is True

    def test_suppress_sets_flag(self, tenant, lead, advisor):
        """BRU-19: suppress must set is_suppressed=True."""
        LeadService.suppress(lead=lead, actor=advisor)
        lead.refresh_from_db()
        assert lead.is_suppressed is True
