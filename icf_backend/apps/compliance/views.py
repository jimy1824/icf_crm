from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsSuperAdmin
from apps.compliance.models import RetentionRecord, SupervisionReview
from apps.compliance.serializers import (
    LegalHoldLiftSerializer,
    LegalHoldPlaceSerializer,
    RetentionPolicyConfigSerializer,
    RetentionPolicySerializer,
    RetentionRecordSerializer,
    ReviewActionSerializer,
    ReviewRejectSerializer,
    SupervisionReviewSerializer,
    SupervisionRuleSerializer,
)
from apps.compliance.services import LegalHoldService, RetentionService, SupervisionService


def _drf(exc: DjangoValidationError):
    from rest_framework.exceptions import ValidationError
    return ValidationError(exc.messages if hasattr(exc, 'messages') else str(exc))


# ---------------------------------------------------------------------------
# Retention policy configuration (Compliance Officer / Super Admin only)
# ---------------------------------------------------------------------------

class RetentionPolicyView(APIView):
    """
    GET  /api/v1/compliance/retention/policies/  — list tenant policies
    POST /api/v1/compliance/retention/policies/  — set/update a policy
    BRU-37, M-C
    """
    permission_classes = [IsAuthenticated]

    def _check_permission(self, user):
        return user.role in ('super_admin', 'compliance_officer', 'tenant_admin')

    def get(self, request):
        if not self._check_permission(request.user):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        from apps.compliance.models import RetentionPolicy
        qs = RetentionPolicy.objects.filter(tenant=request.user.tenant)
        return Response(RetentionPolicySerializer(qs, many=True).data)

    def post(self, request):
        if not self._check_permission(request.user):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        ser = RetentionPolicyConfigSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            policy = RetentionService.configure_policy(
                tenant=request.user.tenant,
                entity_type=d['entity_type'],
                retention_years=d['retention_years'],
                actor=request.user,
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(RetentionPolicySerializer(policy).data, status=status.HTTP_200_OK)


class RetentionRecordListView(APIView):
    """GET /api/v1/compliance/retention/records/ — list records for tenant."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in ('super_admin', 'compliance_officer', 'tenant_admin'):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        qs = RetentionRecord.objects.filter(tenant=request.user.tenant).order_by('-retained_until')
        entity_type = request.query_params.get('entity_type')
        if entity_type:
            qs = qs.filter(entity_type=entity_type)
        return Response(RetentionRecordSerializer(qs, many=True).data)


# ---------------------------------------------------------------------------
# Legal hold (BRU-38)
# ---------------------------------------------------------------------------

class LegalHoldPlaceView(APIView):
    """POST /api/v1/compliance/legal-hold/ — place a hold."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role not in ('super_admin', 'compliance_officer'):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        ser = LegalHoldPlaceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        try:
            record = LegalHoldService.place_hold(
                tenant=request.user.tenant,
                entity_type=d['entity_type'],
                entity_id=d['entity_id'],
                actor=request.user,
                reason=d['reason'],
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(RetentionRecordSerializer(record).data, status=status.HTTP_201_CREATED)


class LegalHoldLiftView(APIView):
    """POST /api/v1/compliance/legal-hold/<entity_type>/<entity_id>/lift/ — lift."""
    permission_classes = [IsAuthenticated]

    def post(self, request, entity_type, entity_id):
        if request.user.role not in ('super_admin', 'compliance_officer'):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        ser = LegalHoldLiftSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            record = LegalHoldService.lift_hold(
                tenant=request.user.tenant,
                entity_type=entity_type,
                entity_id=entity_id,
                actor=request.user,
                reason=ser.validated_data.get('reason', ''),
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(RetentionRecordSerializer(record).data)


# ---------------------------------------------------------------------------
# Supervision review queue (BRU-36)
# ---------------------------------------------------------------------------

class SupervisionReviewListView(APIView):
    """GET /api/v1/compliance/supervision/reviews/ — list reviews for supervisor."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role not in (
            'super_admin', 'compliance_officer', 'tenant_admin', 'team_lead',
        ):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        qs = SupervisionReview.objects.filter(
            tenant=request.user.tenant,
        ).select_related('communication', 'rule', 'supervisor', 'reviewed_by')

        # Non-admin supervisors see only their own queue
        if request.user.role not in ('super_admin', 'compliance_officer', 'tenant_admin'):
            qs = qs.filter(supervisor=request.user)

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(SupervisionReviewSerializer(qs, many=True).data)


class SupervisionReviewApproveView(APIView):
    """POST /api/v1/compliance/supervision/reviews/<pk>/approve/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            review = SupervisionReview.objects.get(pk=pk, tenant=request.user.tenant)
        except SupervisionReview.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if request.user.role not in (
            'super_admin', 'compliance_officer', 'tenant_admin', 'team_lead',
        ) and review.supervisor_id != request.user.pk:
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        ser = ReviewActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            review = SupervisionService.approve(
                review=review, reviewer=request.user, notes=ser.validated_data.get('notes', ''),
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(SupervisionReviewSerializer(review).data)


class SupervisionReviewRejectView(APIView):
    """POST /api/v1/compliance/supervision/reviews/<pk>/reject/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            review = SupervisionReview.objects.get(pk=pk, tenant=request.user.tenant)
        except SupervisionReview.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if request.user.role not in (
            'super_admin', 'compliance_officer', 'tenant_admin', 'team_lead',
        ) and review.supervisor_id != request.user.pk:
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        ser = ReviewRejectSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            review = SupervisionService.reject(
                review=review, reviewer=request.user, notes=ser.validated_data['notes'],
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(SupervisionReviewSerializer(review).data)


class SupervisionReviewEscalateView(APIView):
    """POST /api/v1/compliance/supervision/reviews/<pk>/escalate/"""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            review = SupervisionReview.objects.get(pk=pk, tenant=request.user.tenant)
        except SupervisionReview.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        ser = ReviewActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            review = SupervisionService.escalate(
                review=review, reviewer=request.user, notes=ser.validated_data.get('notes', ''),
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(SupervisionReviewSerializer(review).data)
