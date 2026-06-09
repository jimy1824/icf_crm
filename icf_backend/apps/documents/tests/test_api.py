import pytest
from rest_framework.test import APIClient

from apps.documents.models import Document
from apps.documents.services import DocumentService
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
        status=Lead.STATUS_CLIENT,
    )


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def auth_client(api_client, advisor):
    api_client.force_authenticate(user=advisor)
    return api_client


@pytest.fixture
def compliance_client(api_client, compliance):
    api_client.force_authenticate(user=compliance)
    return api_client


@pytest.fixture
def pending_doc(tenant, lead_obj, advisor):
    return DocumentService.upload_document(
        tenant=tenant, lead=lead_obj, actor=advisor,
        doc_type=Document.TYPE_IDENTITY,
        storage_ref='s3://bucket/id.pdf',
    )


# ---------------------------------------------------------------------------
# Document upload / list / delete
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestDocumentAPI:

    def test_upload_document(self, auth_client, lead_obj):
        url = f'/api/v1/documents/leads/{lead_obj.pk}/documents/'
        resp = auth_client.post(url, {
            'doc_type': 'financial',
            'storage_ref': 's3://bucket/statement.pdf',
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['kyc_status'] == 'pending'

    def test_list_documents(self, auth_client, lead_obj, pending_doc):
        url = f'/api/v1/documents/leads/{lead_obj.pk}/documents/'
        resp = auth_client.get(url)
        assert resp.status_code == 200
        assert len(resp.data) == 1

    def test_retrieve_document(self, auth_client, lead_obj, pending_doc):
        url = f'/api/v1/documents/leads/{lead_obj.pk}/documents/{pending_doc.pk}/'
        resp = auth_client.get(url)
        assert resp.status_code == 200
        assert resp.data['id'] == pending_doc.pk

    def test_delete_document(self, auth_client, lead_obj, pending_doc):
        url = f'/api/v1/documents/leads/{lead_obj.pk}/documents/{pending_doc.pk}/'
        resp = auth_client.delete(url)
        assert resp.status_code == 204
        assert not Document.objects.filter(pk=pending_doc.pk).exists()

    def test_bru_32_call_recording_without_consent_rejected(self, auth_client, lead_obj):
        url = f'/api/v1/documents/leads/{lead_obj.pk}/documents/'
        resp = auth_client.post(url, {
            'doc_type': 'call_recording',
            'storage_ref': 's3://bucket/call.mp4',
            'consent_captured': False,
        }, format='json')
        assert resp.status_code == 400

    def test_unauthenticated_rejected(self, api_client, lead_obj):
        url = f'/api/v1/documents/leads/{lead_obj.pk}/documents/'
        resp = api_client.get(url)
        assert resp.status_code == 401

    def test_bru_01_cross_tenant_isolation(self, api_client):
        """BRU-01: advisor from Firm A cannot see Firm B documents."""
        t2 = Tenant.objects.create(firm_name='Other Firm')
        lead2 = Lead.objects.create(
            tenant=t2, first_name='X', last_name='Y',
            email='x@other.com', source=Lead.SOURCE_MANUAL,
            status=Lead.STATUS_CLIENT,
        )
        doc2 = Document.objects.create(
            tenant=t2, lead=lead2,
            doc_type=Document.TYPE_TAX,
            storage_ref='s3://other/tax.pdf',
        )
        t1 = Tenant.objects.create(firm_name='Firm A')
        advisor_a = CustomUser.objects.create_user(
            email='a@firma.com', password='pass1234!',
            first_name='A', last_name='A',
            role=CustomUser.ROLE_ADVISOR, tenant=t1,
        )
        api_client.force_authenticate(user=advisor_a)
        url = f'/api/v1/documents/leads/{lead2.pk}/documents/'
        resp = api_client.get(url)
        assert resp.status_code in [403, 404]


# ---------------------------------------------------------------------------
# KYC lifecycle
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestKYCLifecycleAPI:

    def test_verify_document(self, compliance_client, lead_obj, pending_doc):
        """BRU-30: Pending → Verified via API."""
        url = f'/api/v1/documents/leads/{lead_obj.pk}/documents/{pending_doc.pk}/verify/'
        resp = compliance_client.post(url)
        assert resp.status_code == 200
        assert resp.data['kyc_status'] == 'verified'

    def test_reject_document(self, compliance_client, lead_obj, pending_doc):
        """BRU-30: Pending → Rejected via API."""
        url = f'/api/v1/documents/leads/{lead_obj.pk}/documents/{pending_doc.pk}/reject/'
        resp = compliance_client.post(url, {'reason': 'Photo unclear'}, format='json')
        assert resp.status_code == 200
        assert resp.data['kyc_status'] == 'rejected'

    def test_advisor_cannot_verify(self, auth_client, lead_obj, pending_doc):
        """Only compliance officers can verify — advisors must get 403."""
        url = f'/api/v1/documents/leads/{lead_obj.pk}/documents/{pending_doc.pk}/verify/'
        resp = auth_client.post(url)
        assert resp.status_code == 403

    def test_legal_hold_blocks_deletion(self, advisor, compliance, lead_obj, pending_doc):
        """BRU-38: deleting a document under legal hold must fail."""
        from rest_framework.test import APIClient as _APIClient
        c_client = _APIClient()
        a_client = _APIClient()
        c_client.force_authenticate(user=compliance)
        a_client.force_authenticate(user=advisor)
        # Place hold
        hold_url = f'/api/v1/documents/leads/{lead_obj.pk}/documents/{pending_doc.pk}/legal-hold/'
        c_client.post(hold_url)
        # Attempt delete
        del_url = f'/api/v1/documents/leads/{lead_obj.pk}/documents/{pending_doc.pk}/'
        resp = a_client.delete(del_url)
        assert resp.status_code == 400  # service raises ValidationError → 400

    def test_kyc_pending_queue(self, compliance_client, lead_obj, pending_doc):
        """Compliance officer sees pending KYC queue."""
        resp = compliance_client.get('/api/v1/documents/documents/kyc-pending/')
        assert resp.status_code == 200
        assert len(resp.data) >= 1
