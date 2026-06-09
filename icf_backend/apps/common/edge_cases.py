"""
Phase 5 edge-case hardening helpers.
E-1: Token expiry mid-campaign
E-2: Duplicate inbound race
E-3: Stop-on-reply race (atomic DB check)
E-4: Cross-tenant identity isolation guard
E-5: Currency/as-of integrity enforcement
"""
from django.core.exceptions import ValidationError


# ---------------------------------------------------------------------------
# E-5: Currency / as-of integrity (BRU-26)
# ---------------------------------------------------------------------------

def assert_currency_consistent(
    existing_currency: str, new_currency: str, field_label: str,
) -> None:
    """
    BRU-26: raise ValidationError if the caller attempts to change currency on
    an existing monetary field without explicitly acknowledging conversion.
    Only the service layer ever calls this; views never bypass it.
    """
    if existing_currency and new_currency and existing_currency != new_currency:
        raise ValidationError(
            f"BRU-26: Cannot silently change currency of {field_label} "
            f"from {existing_currency!r} to {new_currency!r}. "
            "Supply an explicit as_of_date and acknowledge the conversion."
        )


def assert_as_of_not_regressed(
    existing_as_of, new_as_of, field_label: str,
) -> None:
    """
    BRU-26: as-of date must not move backwards on an existing record
    (that would silently backdate a financial figure).
    """
    if existing_as_of and new_as_of and new_as_of < existing_as_of:
        raise ValidationError(
            f"BRU-26: as_of_date for {field_label} cannot be set backwards "
            f"(existing: {existing_as_of}, proposed: {new_as_of})."
        )


# ---------------------------------------------------------------------------
# E-4: Cross-tenant identity isolation (BRU-01)
# ---------------------------------------------------------------------------

def assert_same_tenant(entity, tenant, label: str = "entity") -> None:
    """
    BRU-01: raise ValidationError if the entity's tenant differs from the
    expected tenant. Call this before any cross-entity linking operation
    (e.g., attaching a Lead to a Client, assigning a Household member).
    """
    entity_tenant_id = getattr(entity, 'tenant_id', None)
    expected_id = tenant.pk if hasattr(tenant, 'pk') else tenant
    if entity_tenant_id != expected_id:
        raise ValidationError(
            f"BRU-01: Cannot link {label} — it belongs to a different tenant. "
            "Cross-tenant linking is strictly prohibited."
        )


# ---------------------------------------------------------------------------
# E-1: Token expiry mid-campaign guard (BRU-05)
# ---------------------------------------------------------------------------

def assert_mailbox_active(connection) -> None:
    """
    BRU-05: raise ValidationError if the mailbox connection is not active.
    Call before any outbound send that uses OAuth-backed mailbox.
    """
    from apps.communications.models import MailboxConnection
    if connection.status != MailboxConnection.STATUS_ACTIVE:
        raise ValidationError(
            f"BRU-05: Mailbox connection {connection.pk} is {connection.status!r}. "
            "Reconnect and re-authenticate before sending."
        )
    from django.utils import timezone
    if connection.token_expires_at <= timezone.now():
        raise ValidationError(
            f"BRU-05: OAuth token for mailbox {connection.pk} has expired. "
            "Re-authenticate to resume automation."
        )
