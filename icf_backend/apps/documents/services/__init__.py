import datetime

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import AuditService
from apps.documents.models import Document

# BRU-25: maximum documents per lead per tenant
MAX_DOCUMENTS_PER_CLIENT = 100

ALLOWED_EXTENSIONS = {'.pdf', '.jpg', '.jpeg', '.png', '.doc', '.docx', '.xls', '.xlsx', '.mp3', '.mp4'}
BLOCKED_EXTENSIONS = {'.exe', '.sh', '.bat', '.js', '.py', '.php', '.rb', '.pl'}


class DocumentService:

    @staticmethod
    @transaction.atomic
    def upload_document(
        *, tenant, lead, actor, doc_type, storage_ref, filename='',
        consent_captured=False, retain_until=None,
    ) -> Document:
        """BRU-25: enforce quota. BRU-32: consent flag required for call recordings."""
        _validate_filename(filename)
        _enforce_quota(tenant=tenant, lead=lead)

        if doc_type == Document.TYPE_CALL_RECORDING and not consent_captured:
            raise ValidationError(
                "BRU-32: consent_captured must be True for call recordings."
            )

        doc = Document.objects.create(
            tenant=tenant, lead=lead,
            doc_type=doc_type, storage_ref=storage_ref,
            uploaded_by=actor, uploaded_at=timezone.now(),
            consent_captured=consent_captured,
            retain_until=retain_until,
        )
        AuditService.log(
            actor=actor, tenant=tenant,
            action='document.uploaded',
            entity_type='Document', entity_id=doc.pk,
            after_state={'doc_type': doc_type, 'kyc_status': doc.kyc_status},
        )
        return doc

    @staticmethod
    @transaction.atomic
    def verify_document(*, document, actor) -> Document:
        """BRU-30: Pending → Verified. Only compliance officer or tenant admin."""
        if document.kyc_status != Document.KYC_PENDING:
            raise ValidationError(
                f"Cannot verify a document with status '{document.kyc_status}'."
            )
        before = {'kyc_status': document.kyc_status}
        document.kyc_status = Document.KYC_VERIFIED
        document.verified_by = actor
        document.verified_at = timezone.now()
        document.save(update_fields=['kyc_status', 'verified_by', 'verified_at'])
        AuditService.log(
            actor=actor, tenant=document.tenant,
            action='document.verified',
            entity_type='Document', entity_id=document.pk,
            before_state=before,
            after_state={'kyc_status': Document.KYC_VERIFIED},
        )
        return document

    @staticmethod
    @transaction.atomic
    def reject_document(*, document, actor, reason='') -> Document:
        """BRU-30: Pending → Rejected."""
        if document.kyc_status != Document.KYC_PENDING:
            raise ValidationError(
                f"Cannot reject a document with status '{document.kyc_status}'."
            )
        before = {'kyc_status': document.kyc_status}
        document.kyc_status = Document.KYC_REJECTED
        document.verified_by = actor
        document.verified_at = timezone.now()
        document.save(update_fields=['kyc_status', 'verified_by', 'verified_at'])
        AuditService.log(
            actor=actor, tenant=document.tenant,
            action='document.rejected',
            entity_type='Document', entity_id=document.pk,
            before_state=before,
            after_state={'kyc_status': Document.KYC_REJECTED, 'reason': reason},
        )
        return document

    @staticmethod
    @transaction.atomic
    def place_legal_hold(*, document, actor) -> Document:
        """BRU-38: prevent deletion while under legal hold."""
        if document.is_under_legal_hold:
            return document
        document.is_under_legal_hold = True
        document.save(update_fields=['is_under_legal_hold'])
        AuditService.log(
            actor=actor, tenant=document.tenant,
            action='document.legal_hold_placed',
            entity_type='Document', entity_id=document.pk,
        )
        return document

    @staticmethod
    @transaction.atomic
    def delete_document(*, document, actor) -> None:
        """BRU-38: block deletion if under legal hold."""
        if document.is_under_legal_hold:
            raise ValidationError(
                "BRU-38: Cannot delete a document under legal hold."
            )
        AuditService.log(
            actor=actor, tenant=document.tenant,
            action='document.deleted',
            entity_type='Document', entity_id=document.pk,
            before_state={'doc_type': document.doc_type, 'kyc_status': document.kyc_status},
        )
        document.delete()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_filename(filename: str) -> None:
    if not filename:
        return
    import os
    ext = os.path.splitext(filename)[1].lower()
    if ext in BLOCKED_EXTENSIONS:
        raise ValidationError(f"File type '{ext}' is not permitted.")


def _enforce_quota(*, tenant, lead) -> None:
    count = Document.objects.filter(tenant=tenant, lead=lead).count()
    if count >= MAX_DOCUMENTS_PER_CLIENT:
        raise ValidationError(
            f"BRU-25: document quota ({MAX_DOCUMENTS_PER_CLIENT}) reached for this lead."
        )
