from django.db import transaction
from django.core.exceptions import ValidationError

from apps.leads.models import Lead, KanbanCard, ActivityNote, ConsentRecord
from apps.audit.services import AuditService


class LeadService:

    @staticmethod
    @transaction.atomic
    def create_lead(
        *,
        tenant,
        first_name: str,
        last_name: str,
        email: str,
        phone: str = '',
        source: str = Lead.SOURCE_MANUAL,
        territory_name: str = '',
        actor=None,
    ) -> Lead:
        """
        FR-08.1: manual and auto lead creation.
        BRU-16: idempotent — if tenant+email already exists, return the existing lead.
        BRU-02: source is validated by caller.
        """
        existing = Lead.objects.filter(tenant=tenant, email=email).first()
        if existing:
            return existing

        territory = None
        if territory_name:
            from apps.territories.services import TerritoryService
            territory = TerritoryService.resolve_or_warn(
                tenant=tenant, territory_name=territory_name,
            )

        lead = Lead(
            tenant=tenant,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone=phone,
            source=source,
            status=Lead.STATUS_LEAD,
            pipeline_stage=Lead.STAGE_NEW,
            territory=territory,
        )
        lead.full_clean()
        lead.save()

        KanbanCard.objects.create(lead=lead, stage=Lead.STAGE_NEW, position=0)

        body = f"Lead created via {lead.get_source_display()}."
        if territory:
            body += f" Territory: {territory.name}."
        ActivityNote.objects.create(
            tenant=tenant,
            lead=lead,
            author=actor,
            activity_type=ActivityNote.TYPE_SYSTEM,
            body=body,
            is_private=True,
        )

        AuditService.log(
            actor=actor,
            tenant=tenant,
            action='lead.create',
            entity_type='Lead',
            entity_id=lead.pk,
            after_state={
                'email': lead.email,
                'source': lead.source,
                'status': lead.status,
                'territory_id': territory.pk if territory else None,
            },
        )

        if territory:
            from apps.territories.tasks import distribute_lead_to_territory
            distribute_lead_to_territory.delay(lead.pk)

        return lead

    @staticmethod
    @transaction.atomic
    def assign_advisors(*, lead: Lead, advisor_ids: list, actor=None) -> Lead:
        """
        FR-08.3 / BRU-06: assign ≥1 advisor.
        BRU-22: reassignment preserves history.
        """
        from apps.users.models import CustomUser

        advisors = CustomUser.objects.filter(
            pk__in=advisor_ids,
            tenant=lead.tenant,
            role__in=[CustomUser.ROLE_ADVISOR, CustomUser.ROLE_TEAM_LEAD],
            is_active=True,
        )
        if not advisors.exists():
            raise ValidationError("At least one valid advisor in this tenant is required (BRU-06).")

        before = list(lead.assigned_advisors.values_list('pk', flat=True))
        lead.assigned_advisors.set(advisors)

        ActivityNote.objects.create(
            tenant=lead.tenant,
            lead=lead,
            author=actor,
            activity_type=ActivityNote.TYPE_SYSTEM,
            body=f"Lead assigned to: {', '.join(a.get_full_name() for a in advisors)}.",
            is_private=True,
        )

        AuditService.log(
            actor=actor,
            tenant=lead.tenant,
            action='lead.assign',
            entity_type='Lead',
            entity_id=lead.pk,
            before_state={'assigned_advisors': [str(pk) for pk in before]},
            after_state={'assigned_advisors': [str(a.pk) for a in advisors]},
        )
        return lead

    @staticmethod
    @transaction.atomic
    def move_stage(*, lead: Lead, new_stage: str, position: int = 0, actor=None) -> KanbanCard:
        """
        FM-18 / BRU-31: stage move atomically updates lead.status + kanban card +
        timeline entry + audit entry.
        """
        if new_stage not in dict(Lead.STAGE_CHOICES):
            raise ValidationError(f"'{new_stage}' is not a valid pipeline stage.")

        old_stage = lead.pipeline_stage
        new_status = Lead.STAGE_TO_STATUS[new_stage]

        lead.pipeline_stage = new_stage
        lead.status = new_status
        lead.save(update_fields=['pipeline_stage', 'status', 'updated_at'])

        card = lead.kanban_card
        card.stage = new_stage
        card.position = position
        card.save(update_fields=['stage', 'position', 'updated_at'])

        ActivityNote.objects.create(
            tenant=lead.tenant,
            lead=lead,
            author=actor,
            activity_type=ActivityNote.TYPE_STAGE_CHANGE,
            body=f"Stage moved from '{old_stage}' to '{new_stage}' (status: {new_status}).",
            is_private=True,
        )

        AuditService.log(
            actor=actor,
            tenant=lead.tenant,
            action='lead.stage_change',
            entity_type='Lead',
            entity_id=lead.pk,
            before_state={'pipeline_stage': old_stage},
            after_state={'pipeline_stage': new_stage, 'status': new_status},
        )
        return card

    @staticmethod
    @transaction.atomic
    def convert_to_client(*, lead: Lead, actor=None) -> Lead:
        """
        FM-08: convert a lead/prospect to a client.
        Sets status='client', moves kanban to closed_won, writes timeline + audit.
        The Lead record IS the client — no separate Client object is created.
        BRU-31: atomically updates status + stage + timeline + audit.
        """
        if lead.status == Lead.STATUS_CLIENT:
            raise ValidationError("This lead is already a client.")
        if lead.status in Lead.TERMINAL_STATUSES:
            raise ValidationError(f"A lead with status '{lead.status}' cannot be converted.")

        old_status = lead.status
        lead.status = Lead.STATUS_CLIENT
        lead.pipeline_stage = Lead.STAGE_CLOSED_WON
        lead.save(update_fields=['status', 'pipeline_stage', 'updated_at'])

        # Update kanban card
        card = lead.kanban_card
        card.stage = Lead.STAGE_CLOSED_WON
        card.save(update_fields=['stage', 'updated_at'])

        ActivityNote.objects.create(
            tenant=lead.tenant,
            lead=lead,
            author=actor,
            activity_type=ActivityNote.TYPE_SYSTEM,
            body=f"Status changed from '{old_status}' to 'client'. Lead converted to client.",
            is_private=True,
        )

        AuditService.log(
            actor=actor,
            tenant=lead.tenant,
            action='lead.convert_to_client',
            entity_type='Lead',
            entity_id=lead.pk,
            before_state={'status': old_status},
            after_state={'status': Lead.STATUS_CLIENT},
        )

        from apps.common.events import event_bus
        event_bus.emit(
            'lead.converted_to_client',
            tenant_id=str(lead.tenant_id),
            lead_id=str(lead.pk),
        )

        return lead

    @staticmethod
    @transaction.atomic
    def add_note(
        *,
        tenant,
        lead: Lead,
        author,
        body: str,
        activity_type: str = ActivityNote.TYPE_NOTE,
        is_private: bool = True,
    ) -> ActivityNote:
        """
        FM-10 / BRU-08 / BRU-12: add a note to the activity timeline.
        is_private=True (default) — never exposed to Customer Portal.
        """
        note = ActivityNote.objects.create(
            tenant=tenant,
            lead=lead,
            author=author,
            activity_type=activity_type,
            body=body,
            is_private=is_private,
        )

        AuditService.log(
            actor=author,
            tenant=tenant,
            action='timeline.note_added',
            entity_type='Lead',
            entity_id=lead.pk,
            after_state={
                'activity_type': activity_type,
                'is_private': is_private,
            },
        )
        return note

    @staticmethod
    def record_consent(
        *,
        tenant,
        lead: Lead,
        channel: str,
        purpose: str,
        state: str,
        source: str,
    ) -> ConsentRecord:
        """FM-24 / BRU-07 / BRU-15: append-only consent record."""
        return ConsentRecord.objects.create(
            tenant=tenant,
            lead=lead,
            channel=channel,
            purpose=purpose,
            state=state,
            source=source,
        )

    @staticmethod
    def opt_out(*, lead: Lead, actor=None) -> Lead:
        """BRU-07: once opted out, no further automated communications."""
        lead.opted_out = True
        lead.save(update_fields=['opted_out', 'updated_at'])
        AuditService.log(
            actor=actor,
            tenant=lead.tenant,
            action='lead.opt_out',
            entity_type='Lead',
            entity_id=lead.pk,
        )
        return lead

    @staticmethod
    def suppress(*, lead: Lead, actor=None) -> Lead:
        """BRU-19: suppress on bounce / spam complaint / SMS opt-out keyword."""
        lead.is_suppressed = True
        lead.save(update_fields=['is_suppressed', 'updated_at'])
        AuditService.log(
            actor=actor,
            tenant=lead.tenant,
            action='lead.suppress',
            entity_type='Lead',
            entity_id=lead.pk,
        )
        return lead
