from apps.audit.models import AuditEvent


class AuditService:
    """
    Central write path for BRU-33: every significant action writes an
    append-only, tamper-evident audit entry. Call from services, never
    from views or serializers.
    """

    @staticmethod
    def log(
        *,
        actor,
        tenant,
        action: str,
        entity_type: str,
        entity_id,
        before_state=None,
        after_state=None,
        ip_address=None,
    ) -> AuditEvent:
        return AuditEvent.objects.create(
            actor=actor,
            tenant=tenant,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            before_state=before_state,
            after_state=after_state,
            ip_address=ip_address,
        )

    @staticmethod
    def log_from_request(
        request,
        *,
        action: str,
        entity_type: str,
        entity_id,
        before_state=None,
        after_state=None,
    ) -> AuditEvent:
        """Convenience wrapper that extracts actor/tenant/IP from a DRF request."""
        forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
        ip = forwarded.split(',')[0].strip() if forwarded else request.META.get('REMOTE_ADDR')
        return AuditService.log(
            actor=request.user if request.user.is_authenticated else None,
            tenant=getattr(request.user, 'tenant', None),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            ip_address=ip or None,
        )
