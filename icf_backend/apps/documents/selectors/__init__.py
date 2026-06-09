from apps.documents.models import Document


def get_documents_for_lead(*, tenant, lead):
    """BRU-01: always scoped to tenant."""
    return (
        Document.objects
        .filter(tenant=tenant, lead=lead)
        .select_related('uploaded_by', 'verified_by')
        .order_by('-uploaded_at')
    )


def get_pending_kyc(*, tenant):
    return (
        Document.objects
        .filter(tenant=tenant, kyc_status=Document.KYC_PENDING)
        .select_related('lead', 'uploaded_by')
        .order_by('uploaded_at')
    )


def get_document_by_id(*, tenant, pk) -> Document | None:
    return Document.objects.filter(tenant=tenant, pk=pk).first()
