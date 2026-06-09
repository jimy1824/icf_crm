"""
Portal services — business logic for customer portal operations.
Thin services that delegate queries to selectors and enforce BRU rules.
"""

from django.db import transaction
from django.utils import timezone

from apps.audit.services import AuditService
from apps.users.models import CustomerAccount


class CustomerAccountService:
    """
    Create and manage CustomerAccount records (portal access provisioning).
    Called by tenant admin views when enabling portal access for a lead.
    """

    @staticmethod
    @transaction.atomic
    def provision_portal_access(*, lead, password: str, actor) -> CustomerAccount:
        """
        Create a CustomerAccount for a Lead and enable portal access.
        Idempotent: returns existing account if already provisioned.
        """
        if hasattr(lead, 'customer_account'):
            account = lead.customer_account
            if not account.is_active:
                account.is_active = True
                account.save(update_fields=['is_active'])
            if not lead.portal_enabled:
                lead.portal_enabled = True
                lead.save(update_fields=['portal_enabled'])
            return account

        account = CustomerAccount.objects.create_user(
            email=lead.email,
            lead=lead,
            tenant=lead.tenant,
            password=password,
        )
        lead.portal_enabled = True
        lead.save(update_fields=['portal_enabled'])

        AuditService.log(
            actor=actor,
            tenant=lead.tenant,
            action='portal.provision_access',
            entity_type='CustomerAccount',
            entity_id=account.pk,
            after_state={'email': account.email, 'lead_id': str(lead.pk)},
        )
        return account

    @staticmethod
    @transaction.atomic
    def revoke_portal_access(*, lead, actor) -> None:
        """Deactivate portal access for a lead."""
        if hasattr(lead, 'customer_account'):
            account = lead.customer_account
            account.is_active = False
            account.save(update_fields=['is_active'])

        lead.portal_enabled = False
        lead.save(update_fields=['portal_enabled'])

        AuditService.log(
            actor=actor,
            tenant=lead.tenant,
            action='portal.revoke_access',
            entity_type='Lead',
            entity_id=lead.pk,
        )
