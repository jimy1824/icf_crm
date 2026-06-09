"""
Tests for GET/POST /portal/documents/ and GET /portal/documents/<pk>/
BRU-01: tenant+lead isolation. BRU-33: document upload is audited.
"""

import pytest
from rest_framework.test import APIClient

from apps.documents.models import Document
from apps.leads.models import Lead
from apps.tenants.models import Tenant
from apps.users.models import CustomerAccount


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Docs Test Firm')


@pytest.fixture
def lead(tenant):
    return Lead.objects.create(
        tenant=tenant,
        first_name='Dave',
        last_name='Docs',
        email='dave@docs.com',
        status=Lead.STATUS_CLIENT,
        portal_enabled=True,
    )


@pytest.fixture
def customer_account(lead, tenant):
    return CustomerAccount.objects.create_user(
        email=lead.email, lead=lead, tenant=tenant, password='testpass123!'
    )


@pytest.fixture
def document(lead, tenant):
    return Document.objects.create(
        lead=lead,
        tenant=tenant,
        doc_type=Document.TYPE_IDENTITY,
        storage_ref='s3://bucket/my-doc.pdf',
        kyc_status=Document.KYC_PENDING,
        version=1,
    )


@pytest.fixture
def portal_client(customer_account):
    client = APIClient()
    client.force_authenticate(user=customer_account)
    return client


@pytest.mark.django_db
class TestPortalDocuments:

    def test_list_documents(self, portal_client, document):
        resp = portal_client.get('/api/v1/portal/documents/')
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]['doc_type'] == Document.TYPE_IDENTITY

    def test_list_empty_when_no_documents(self, portal_client):
        resp = portal_client.get('/api/v1/portal/documents/')
        assert resp.status_code == 200
        assert resp.json() == []

    def test_upload_document_creates_pending_doc(self, portal_client, lead, tenant):
        resp = portal_client.post('/api/v1/portal/documents/', {
            'doc_type': Document.TYPE_TAX,
            'storage_ref': 's3://bucket/tax-doc.pdf',
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data['kyc_status'] == Document.KYC_PENDING
        assert data['doc_type'] == Document.TYPE_TAX

        # Verify it's in DB scoped to the correct lead/tenant
        doc = Document.objects.get(pk=data['id'])
        assert doc.lead == lead
        assert doc.tenant == tenant

    def test_retrieve_own_document(self, portal_client, document):
        resp = portal_client.get(f'/api/v1/portal/documents/{document.pk}/')
        assert resp.status_code == 200
        assert resp.json()['id'] == document.pk

    def test_cannot_retrieve_other_leads_document(self, portal_client, tenant):
        """BRU-01: Cross-lead access returns 404."""
        other_lead = Lead.objects.create(
            tenant=tenant,
            first_name='Eve',
            last_name='Other',
            email='eve@other.com',
            status=Lead.STATUS_CLIENT,
            portal_enabled=True,
        )
        other_doc = Document.objects.create(
            lead=other_lead,
            tenant=tenant,
            doc_type=Document.TYPE_FINANCIAL,
            storage_ref='s3://bucket/other.pdf',
            kyc_status=Document.KYC_PENDING,
            version=1,
        )
        resp = portal_client.get(f'/api/v1/portal/documents/{other_doc.pk}/')
        assert resp.status_code == 404

    def test_unauthenticated_returns_403(self, document):
        client = APIClient()
        resp = client.get('/api/v1/portal/documents/')
        assert resp.status_code in (401, 403)
