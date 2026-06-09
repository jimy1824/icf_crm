import pytest
from apps.documents.models import Document
from apps.tenants.models import Tenant
from apps.leads.models import Lead


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm')


@pytest.fixture
def lead_obj(tenant):
    return Lead.objects.create(
        tenant=tenant, first_name='Ana', last_name='Bell',
        email='ana@example.com', source=Lead.SOURCE_MANUAL,
        status=Lead.STATUS_CLIENT,
    )


@pytest.mark.django_db
class TestDocument:
    def test_default_kyc_status(self, tenant, lead_obj):
        doc = Document.objects.create(
            tenant=tenant,
            lead=lead_obj,
            doc_type=Document.TYPE_IDENTITY,
            storage_ref='s3://bucket/id.pdf',
        )
        assert doc.kyc_status == Document.KYC_PENDING
        assert doc.is_under_legal_hold is False
        assert doc.version == 1

    def test_legal_hold_flag(self, tenant, lead_obj):
        doc = Document.objects.create(
            tenant=tenant, lead=lead_obj,
            doc_type=Document.TYPE_TAX,
            storage_ref='s3://bucket/tax.pdf',
            is_under_legal_hold=True,
        )
        assert doc.is_under_legal_hold is True
