from apps.audit.models import AuditEvent


def get_audit_trail(*, tenant, entity_type=None, entity_id=None):
    # BRU-01
    qs = AuditEvent.objects.filter(tenant=tenant)
    if entity_type:
        qs = qs.filter(entity_type=entity_type)
    if entity_id:
        qs = qs.filter(entity_id=str(entity_id))
    return qs


def get_actor_history(*, tenant, actor):
    return AuditEvent.objects.filter(tenant=tenant, actor=actor)
