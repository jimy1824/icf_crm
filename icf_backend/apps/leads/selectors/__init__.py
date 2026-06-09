from apps.leads.models import Lead, KanbanCard, ActivityNote, ConsentRecord


def get_leads_for_tenant(*, tenant, status=None, statuses=None, stage=None, advisor=None, territory=None):
    """BRU-01: always scoped to tenant. Supports filtering by status(es), stage, advisor, territory."""
    qs = (
        Lead.objects
        .filter(tenant=tenant)
        .select_related('territory', 'household')
        .prefetch_related('assigned_advisors')
    )
    if status:
        qs = qs.filter(status=status)
    if statuses:
        qs = qs.filter(status__in=statuses)
    if stage:
        qs = qs.filter(pipeline_stage=stage)
    if advisor:
        qs = qs.filter(assigned_advisors=advisor)
    if territory:
        qs = qs.filter(territory=territory)
    return qs


def get_clients_for_tenant(*, tenant, advisor=None):
    """Return leads that are in a client-stage status (BRU-01)."""
    return get_leads_for_tenant(
        tenant=tenant,
        statuses=list(Lead.CLIENT_STATUSES),
        advisor=advisor,
    )


def get_pipeline_leads_for_tenant(*, tenant, advisor=None):
    """Return leads in pre-conversion pipeline stages (BRU-01)."""
    return get_leads_for_tenant(
        tenant=tenant,
        statuses=list(Lead.PIPELINE_STATUSES),
        advisor=advisor,
    )


def get_lead_by_id(*, lead_id, tenant):
    """BRU-01: always cross-checks tenant."""
    return (
        Lead.objects
        .select_related('territory', 'household')
        .prefetch_related('assigned_advisors')
        .get(pk=lead_id, tenant=tenant)
    )


def get_active_pipeline(*, tenant):
    """Exclude terminal-status leads from the active pipeline."""
    return Lead.objects.filter(tenant=tenant).exclude(
        status__in=Lead.TERMINAL_STATUSES
    )


def get_kanban_board(*, tenant, advisor=None):
    """
    FM-18: return all non-terminal leads with their kanban card for the board view.
    BRU-01: scoped to tenant. Optional advisor filter for own-view scope.
    """
    qs = (
        Lead.objects.filter(tenant=tenant)
        .exclude(pipeline_stage__in=[Lead.STAGE_CLOSED_WON, Lead.STAGE_CLOSED_LOST])
        .select_related('kanban_card')
        .prefetch_related('assigned_advisors')
    )
    if advisor:
        qs = qs.filter(assigned_advisors=advisor)
    return qs.order_by('kanban_card__stage', 'kanban_card__position')


def get_timeline(*, tenant, lead, include_private=True):
    """
    FM-10 / BRU-08: fetch activity timeline for a lead.
    include_private=False is used for Customer Portal — never returns private notes.
    """
    qs = ActivityNote.objects.filter(tenant=tenant, lead=lead).select_related('author')
    if not include_private:
        qs = qs.filter(is_private=False)
    return qs.order_by('-created_at')


def get_active_consent(*, tenant, lead, channel: str):
    """
    BRU-15: latest consent record for a channel determines send eligibility.
    Returns None if no record exists (treat as no consent).
    """
    return (
        ConsentRecord.objects
        .filter(tenant=tenant, lead=lead, channel=channel)
        .order_by('-recorded_at')
        .first()
    )


def has_active_consent(*, tenant, lead, channel: str) -> bool:
    """Convenience check: True only if latest consent record has state='granted'."""
    record = get_active_consent(tenant=tenant, lead=lead, channel=channel)
    return record is not None and record.state == ConsentRecord.STATE_GRANTED
