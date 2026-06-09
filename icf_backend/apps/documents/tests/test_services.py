import pytest
from django.core.exceptions import ValidationError

from apps.documents.models import Document
from apps.documents.services import DocumentService, MAX_DOCUMENTS_PER_CLIENT
from apps.leads.models import Lead
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm')


@pytest.fixture
def advisor(tenant):
    return CustomUser.objects.create_user(
        email='advisor@test.com', password='pass1234!',
        first_name='Jane', last_name='Advisor',
        role=CustomUser.ROLE_ADVISOR, tenant=tenant,
    )


@pytest.fixture
def compliance(tenant):
    return CustomUser.objects.create_user(
        email='compliance@test.com', password='pass1234!',
        first_name='Charlie', last_name='Compliance',
        role=CustomUser.ROLE_COMPLIANCE, tenant=tenant,
    )


@pytest.fixture
def lead_obj(tenant):
    return Lead.objects.create(
        tenant=tenant, first_name='Bob', last_name='Client',
        email='bob@test.com', source=Lead.SOURCE_MANUAL,
        pipeline_stage=Lead.STAGE_CLOSED_WON, status=Lead.STATUS_CLIENT,
    )


@pytest.fixture
def pending_doc(tenant, lead_obj, advisor):
    return DocumentService.upload_document(
        tenant=tenant, lead=lead_obj, actor=advisor,
        doc_type=Document.TYPE_IDENTITY,
        storage_ref='s3://bucket/id.pdf',
        filename='id.pdf',
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDocumentUpload:

    def test_upload_creates_document_pending(self, tenant, lead_obj, advisor):
        doc = DocumentService.upload_document(
            tenant=tenant, lead=lead_obj, actor=advisor,
            doc_type=Document.TYPE_FINANCIAL,
            storage_ref='s3://bucket/statement.pdf',
        )
        assert doc.pk is not None
        assert doc.kyc_status == Document.KYC_PENDING

    def test_upload_writes_audit(self, tenant, lead_obj, advisor):
        """BRU-33: uploading must create an audit entry."""
        from apps.audit.models import AuditEvent
        DocumentService.upload_document(
            tenant=tenant, lead=lead_obj, actor=advisor,
            doc_type=Document.TYPE_IDENTITY,
            storage_ref='s3://bucket/id.pdf',
        )
        assert AuditEvent.objects.filter(action='document.uploaded').exists()

    def test_call_recording_requires_consent(self, tenant, lead_obj, advisor):
        """BRU-32: uploading a call recording without consent_captured must fail."""
        with pytest.raises(ValidationError, match='BRU-32'):
            DocumentService.upload_document(
                tenant=tenant, lead=lead_obj, actor=advisor,
                doc_type=Document.TYPE_CALL_RECORDING,
                storage_ref='s3://bucket/call.mp4',
                consent_captured=False,
            )

    def test_call_recording_with_consent_succeeds(self, tenant, lead_obj, advisor):
        """BRU-32: call recording with consent_captured=True must succeed."""
        doc = DocumentService.upload_document(
            tenant=tenant, lead=lead_obj, actor=advisor,
            doc_type=Document.TYPE_CALL_RECORDING,
            storage_ref='s3://bucket/call.mp4',
            consent_captured=True,
        )
        assert doc.consent_captured is True

    def test_blocked_file_extension_raises(self, tenant, lead_obj, advisor):
        """Executable file types must be rejected."""
        with pytest.raises(ValidationError):
            DocumentService.upload_document(
                tenant=tenant, lead=lead_obj, actor=advisor,
                doc_type=Document.TYPE_OTHER,
                storage_ref='s3://bucket/virus.exe',
                filename='virus.exe',
            )

    def test_bru_25_quota_enforcement(self, tenant, lead_obj, advisor):
        """BRU-25: uploading beyond quota must raise ValidationError."""
        for i in range(MAX_DOCUMENTS_PER_CLIENT):
            Document.objects.create(
                tenant=tenant, lead=lead_obj,
                doc_type=Document.TYPE_OTHER,
                storage_ref=f's3://bucket/doc{i}.pdf',
            )
        with pytest.raises(ValidationError, match='BRU-25'):
            DocumentService.upload_document(
                tenant=tenant, lead=lead_obj, actor=advisor,
                doc_type=Document.TYPE_OTHER,
                storage_ref='s3://bucket/overflow.pdf',
            )


@pytest.mark.django_db
class TestKYCLifecycle:

    def test_verify_pending_document(self, pending_doc, compliance):
        """BRU-30: Pending → Verified."""
        doc = DocumentService.verify_document(document=pending_doc, actor=compliance)
        assert doc.kyc_status == Document.KYC_VERIFIED
        assert doc.verified_by == compliance
        assert doc.verified_at is not None

    def test_verify_writes_audit(self, pending_doc, compliance):
        from apps.audit.models import AuditEvent
        DocumentService.verify_document(document=pending_doc, actor=compliance)
        assert AuditEvent.objects.filter(action='document.verified').exists()

    def test_reject_pending_document(self, pending_doc, compliance):
        """BRU-30: Pending → Rejected."""
        doc = DocumentService.reject_document(
            document=pending_doc, actor=compliance, reason='Blurry image'
        )
        assert doc.kyc_status == Document.KYC_REJECTED

    def test_reject_writes_audit(self, pending_doc, compliance):
        from apps.audit.models import AuditEvent
        DocumentService.reject_document(document=pending_doc, actor=compliance, reason='')
        assert AuditEvent.objects.filter(action='document.rejected').exists()

    def test_cannot_verify_already_verified(self, pending_doc, compliance):
        """BRU-30: cannot verify a document that is not pending."""
        DocumentService.verify_document(document=pending_doc, actor=compliance)
        with pytest.raises(ValidationError):
            DocumentService.verify_document(document=pending_doc, actor=compliance)

    def test_cannot_reject_already_verified(self, pending_doc, compliance):
        DocumentService.verify_document(document=pending_doc, actor=compliance)
        with pytest.raises(ValidationError):
            DocumentService.reject_document(document=pending_doc, actor=compliance)


@pytest.mark.django_db
class TestLegalHold:

    def test_place_legal_hold(self, pending_doc, compliance):
        """BRU-38: legal hold flag set."""
        doc = DocumentService.place_legal_hold(document=pending_doc, actor=compliance)
        doc.refresh_from_db()
        assert doc.is_under_legal_hold is True

    def test_cannot_delete_under_legal_hold(self, pending_doc, compliance, advisor):
        """BRU-38: deletion of a held document must raise."""
        DocumentService.place_legal_hold(document=pending_doc, actor=compliance)
        with pytest.raises(ValidationError, match='BRU-38'):
            DocumentService.delete_document(document=pending_doc, actor=advisor)

    def test_can_delete_without_hold(self, pending_doc, advisor):
        """Documents without legal hold can be deleted."""
        DocumentService.delete_document(document=pending_doc, actor=advisor)
        assert not Document.objects.filter(pk=pending_doc.pk).exists()

    def test_delete_writes_audit(self, pending_doc, advisor):
        from apps.audit.models import AuditEvent
        DocumentService.delete_document(document=pending_doc, actor=advisor)
        assert AuditEvent.objects.filter(action='document.deleted').exists()


@pytest.mark.django_db
class TestTenantIsolation:

    def test_bru_01_document_scoped_to_tenant(self, advisor):
        """BRU-01: documents from another tenant must not be accessible."""
        t2 = Tenant.objects.create(firm_name='Other Firm')
        lead2 = Lead.objects.create(
            tenant=t2, first_name='X', last_name='Y',
            email='x@other.com', source=Lead.SOURCE_MANUAL,
            status=Lead.STATUS_CLIENT,
        )
        Document.objects.create(
            tenant=t2, lead=lead2,
            doc_type=Document.TYPE_IDENTITY,
            storage_ref='s3://other/doc.pdf',
        )
        qs = Document.objects.for_tenant(advisor.tenant)
        assert not qs.exists()
