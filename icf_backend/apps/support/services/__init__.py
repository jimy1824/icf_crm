import logging
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import AuditService
from apps.common.events import event_bus
from apps.support.models import SupportTicket, TicketComment

logger = logging.getLogger(__name__)

# Valid status transitions (FM-04)
VALID_TRANSITIONS = {
    SupportTicket.STATUS_OPEN: {
        SupportTicket.STATUS_IN_PROGRESS,
        SupportTicket.STATUS_WAITING,
        SupportTicket.STATUS_RESOLVED,
        SupportTicket.STATUS_CLOSED,
    },
    SupportTicket.STATUS_IN_PROGRESS: {
        SupportTicket.STATUS_WAITING,
        SupportTicket.STATUS_RESOLVED,
        SupportTicket.STATUS_CLOSED,
    },
    SupportTicket.STATUS_WAITING: {
        SupportTicket.STATUS_IN_PROGRESS,
        SupportTicket.STATUS_RESOLVED,
        SupportTicket.STATUS_CLOSED,
    },
    SupportTicket.STATUS_RESOLVED: {
        SupportTicket.STATUS_OPEN,
        SupportTicket.STATUS_CLOSED,
    },
    SupportTicket.STATUS_CLOSED: set(),
}


class SupportService:

    @staticmethod
    @transaction.atomic
    def create_ticket(
        *, tenant, created_by, subject, body,
        category=SupportTicket.CATEGORY_OTHER,
        priority=SupportTicket.PRIORITY_NORMAL,
    ) -> SupportTicket:
        ticket = SupportTicket.objects.create(
            tenant=tenant,
            created_by=created_by,
            subject=subject,
            body=body,
            category=category,
            priority=priority,
            status=SupportTicket.STATUS_OPEN,
        )
        AuditService.log(
            tenant=tenant, actor=created_by,
            action='ticket.created',
            entity_type='SupportTicket', entity_id=ticket.pk,
            after_state={'subject': subject, 'priority': priority, 'category': category},
        )
        event_bus.emit(
            'support.ticket_created',
            tenant_id=tenant.pk,
            ticket_id=ticket.pk,
            priority=priority,
        )
        return ticket

    @staticmethod
    @transaction.atomic
    def transition_status(*, ticket: SupportTicket, new_status: str, actor) -> SupportTicket:
        allowed = VALID_TRANSITIONS.get(ticket.status, set())
        if new_status not in allowed:
            raise ValidationError(
                f"Cannot transition ticket from '{ticket.status}' to '{new_status}'."
            )
        old_status = ticket.status
        ticket.status = new_status
        if new_status == SupportTicket.STATUS_RESOLVED:
            ticket.resolved_at = timezone.now()
        elif new_status == SupportTicket.STATUS_CLOSED:
            ticket.closed_at = timezone.now()
        ticket.save(update_fields=['status', 'resolved_at', 'closed_at', 'updated_at'])
        AuditService.log(
            tenant=ticket.tenant, actor=actor,
            action='ticket.status_changed',
            entity_type='SupportTicket', entity_id=ticket.pk,
            before_state={'status': old_status},
            after_state={'status': new_status},
        )
        return ticket

    @staticmethod
    @transaction.atomic
    def assign_ticket(*, ticket: SupportTicket, assignee, actor) -> SupportTicket:
        ticket.assigned_to = assignee
        if ticket.status == SupportTicket.STATUS_OPEN:
            ticket.status = SupportTicket.STATUS_IN_PROGRESS
        ticket.save(update_fields=['assigned_to', 'status', 'updated_at'])
        AuditService.log(
            tenant=ticket.tenant, actor=actor,
            action='ticket.assigned',
            entity_type='SupportTicket', entity_id=ticket.pk,
            after_state={'assigned_to': assignee.pk},
        )
        return ticket

    @staticmethod
    @transaction.atomic
    def add_comment(
        *, ticket: SupportTicket, author, body: str, is_internal: bool = False,
    ) -> TicketComment:
        comment = TicketComment.objects.create(
            ticket=ticket,
            author=author,
            body=body,
            is_internal=is_internal,
        )
        # Move back to in_progress if waiting (customer replied)
        if ticket.status == SupportTicket.STATUS_WAITING and not is_internal:
            ticket.status = SupportTicket.STATUS_IN_PROGRESS
            ticket.save(update_fields=['status', 'updated_at'])
        return comment
