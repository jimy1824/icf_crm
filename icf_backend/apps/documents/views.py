from django.core.exceptions import ValidationError as DjangoValidationError

from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.leads.models import Lead
from rest_framework.exceptions import NotFound

from apps.common.mixins import TenantScopedViewMixin, TenantScopedRequestMixin
from apps.common.permissions import IsAdvisorOrAbove, IsComplianceOfficer, IsTenantMember
from apps.documents.models import Document
from apps.documents.selectors import (
    get_document_by_id,
    get_documents_for_lead,
    get_pending_kyc,
)
from apps.documents.serializers import (
    DocumentSerializer,
    DocumentUploadSerializer,
    DocumentVerifySerializer,
)
from apps.documents.services import DocumentService


def _django_validation_to_drf(exc: DjangoValidationError) -> DRFValidationError:
    messages = list(exc.messages) if hasattr(exc, 'messages') else [str(exc)]
    return DRFValidationError(detail=messages)


class DocumentViewSet(TenantScopedViewMixin, viewsets.ViewSet):
    """
    FM-11: document upload, list, retrieve, delete.
    BRU-25: quota enforced at service layer.
    BRU-38: legal hold blocks deletion.
    """
    permission_classes = [IsAdvisorOrAbove]

    def _get_lead(self, request, lead_pk):
        try:
            return Lead.objects.get(pk=lead_pk, tenant=request.tenant)
        except Lead.DoesNotExist:
            raise NotFound("Lead not found.")

    def list(self, request, lead_pk=None):
        lead = self._get_lead(request, lead_pk)
        qs = get_documents_for_lead(tenant=request.tenant, lead=lead)
        return Response(DocumentSerializer(qs, many=True).data)

    def create(self, request, lead_pk=None):
        lead = self._get_lead(request, lead_pk)
        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            doc = DocumentService.upload_document(
                tenant=request.tenant, lead=lead, actor=request.user,
                **serializer.validated_data,
            )
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)
        return Response(DocumentSerializer(doc).data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, lead_pk=None, pk=None):
        doc = get_document_by_id(tenant=request.tenant, pk=pk)
        if doc is None or doc.lead_id != int(lead_pk):
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(DocumentSerializer(doc).data)

    def destroy(self, request, lead_pk=None, pk=None):
        doc = get_document_by_id(tenant=request.tenant, pk=pk)
        if doc is None or doc.lead_id != int(lead_pk):
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            DocumentService.delete_document(document=doc, actor=request.user)
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)
        return Response(status=status.HTTP_204_NO_CONTENT)


class DocumentKYCView(TenantScopedRequestMixin, APIView):
    """
    BRU-30: KYC lifecycle actions — compliance officers only.
    Separate view so permission enforcement is unambiguous with explicit URLs.
    """
    permission_classes = [IsComplianceOfficer]

    def _get_doc(self, request, lead_pk, pk):
        doc = get_document_by_id(tenant=request.tenant, pk=pk)
        if doc is None or doc.lead_id != int(lead_pk):
            return None
        return doc

    def post(self, request, lead_pk, pk, action_name):
        doc = self._get_doc(request, lead_pk, pk)
        if doc is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            if action_name == 'verify':
                doc = DocumentService.verify_document(document=doc, actor=request.user)
            elif action_name == 'reject':
                serializer = DocumentVerifySerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                doc = DocumentService.reject_document(
                    document=doc, actor=request.user,
                    reason=serializer.validated_data['reason'],
                )
            elif action_name == 'legal-hold':
                doc = DocumentService.place_legal_hold(document=doc, actor=request.user)
            else:
                return Response(status=status.HTTP_404_NOT_FOUND)
        except DjangoValidationError as exc:
            raise _django_validation_to_drf(exc)
        return Response(DocumentSerializer(doc).data)


class PendingKYCViewSet(TenantScopedViewMixin, viewsets.ViewSet):
    """FM-11: compliance queue of documents awaiting KYC review."""
    permission_classes = [IsComplianceOfficer]

    def list(self, request):
        qs = get_pending_kyc(tenant=request.tenant)
        return Response(DocumentSerializer(qs, many=True).data)
