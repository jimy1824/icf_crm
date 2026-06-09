"""
Tests for FM-04: Support ticketing service.
"""
import pytest
from django.core.exceptions import ValidationError

from apps.support.models import SupportTicket, TicketComment
from apps.support.services import SupportService
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm')


@pytest.fixture
def user(db, tenant):
    return CustomUser.objects.create_user(
        email='user@firm.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Jane', last_name='Doe',
    )


@pytest.fixture
def support_user(db, tenant):
    return CustomUser.objects.create_user(
        email='support@platform.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_SUPPORT,
        first_name='Bob', last_name='Support',
    )


@pytest.fixture
def ticket(db, tenant, user):
    return SupportService.create_ticket(
        tenant=tenant, created_by=user,
        subject='Login broken', body='Cannot log in',
        category=SupportTicket.CATEGORY_TECHNICAL,
        priority=SupportTicket.PRIORITY_HIGH,
    )


@pytest.mark.django_db
class TestCreateTicket:

    def test_creates_with_open_status(self, tenant, user):
        ticket = SupportService.create_ticket(
            tenant=tenant, created_by=user,
            subject='Help', body='Need help',
        )
        assert ticket.pk is not None
        assert ticket.status == SupportTicket.STATUS_OPEN
        assert ticket.tenant == tenant
        assert ticket.created_by == user

    def test_default_category_and_priority(self, tenant, user):
        ticket = SupportService.create_ticket(
            tenant=tenant, created_by=user,
            subject='Question', body='?',
        )
        assert ticket.category == SupportTicket.CATEGORY_OTHER
        assert ticket.priority == SupportTicket.PRIORITY_NORMAL


@pytest.mark.django_db
class TestTransitionStatus:

    def test_open_to_in_progress(self, ticket, support_user):
        t = SupportService.transition_status(
            ticket=ticket, new_status=SupportTicket.STATUS_IN_PROGRESS, actor=support_user,
        )
        assert t.status == SupportTicket.STATUS_IN_PROGRESS

    def test_open_to_resolved(self, ticket, support_user):
        t = SupportService.transition_status(
            ticket=ticket, new_status=SupportTicket.STATUS_RESOLVED, actor=support_user,
        )
        assert t.status == SupportTicket.STATUS_RESOLVED
        assert t.resolved_at is not None

    def test_closed_is_terminal(self, ticket, support_user):
        SupportService.transition_status(
            ticket=ticket, new_status=SupportTicket.STATUS_CLOSED, actor=support_user,
        )
        ticket.refresh_from_db()
        with pytest.raises(ValidationError):
            SupportService.transition_status(
                ticket=ticket, new_status=SupportTicket.STATUS_OPEN, actor=support_user,
            )

    def test_invalid_transition_raises(self, ticket, support_user):
        with pytest.raises(ValidationError):
            SupportService.transition_status(
                ticket=ticket, new_status='bogus_status', actor=support_user,
            )


@pytest.mark.django_db
class TestAssignTicket:

    def test_assign_moves_to_in_progress(self, ticket, support_user):
        assert ticket.status == SupportTicket.STATUS_OPEN
        t = SupportService.assign_ticket(
            ticket=ticket, assignee=support_user, actor=support_user,
        )
        assert t.assigned_to == support_user
        assert t.status == SupportTicket.STATUS_IN_PROGRESS

    def test_assign_already_in_progress_keeps_status(self, ticket, support_user):
        ticket.status = SupportTicket.STATUS_IN_PROGRESS
        ticket.save()
        t = SupportService.assign_ticket(
            ticket=ticket, assignee=support_user, actor=support_user,
        )
        assert t.status == SupportTicket.STATUS_IN_PROGRESS


@pytest.mark.django_db
class TestAddComment:

    def test_add_public_comment(self, ticket, user):
        comment = SupportService.add_comment(
            ticket=ticket, author=user, body='More details here.',
        )
        assert comment.pk is not None
        assert comment.is_internal is False

    def test_add_internal_note(self, ticket, support_user):
        comment = SupportService.add_comment(
            ticket=ticket, author=support_user, body='Internal note.', is_internal=True,
        )
        assert comment.is_internal is True

    def test_customer_reply_moves_waiting_to_in_progress(self, ticket, user, support_user):
        # Put ticket in waiting state
        ticket.status = SupportTicket.STATUS_WAITING
        ticket.save()
        SupportService.add_comment(ticket=ticket, author=user, body='Still waiting.')
        ticket.refresh_from_db()
        assert ticket.status == SupportTicket.STATUS_IN_PROGRESS

    def test_internal_note_does_not_change_waiting_status(self, ticket, support_user):
        ticket.status = SupportTicket.STATUS_WAITING
        ticket.save()
        SupportService.add_comment(
            ticket=ticket, author=support_user, body='Internal.', is_internal=True,
        )
        ticket.refresh_from_db()
        assert ticket.status == SupportTicket.STATUS_WAITING
