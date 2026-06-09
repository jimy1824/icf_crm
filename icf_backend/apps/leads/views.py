from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.leads.models import Lead
from apps.leads.serializers import (
    LeadSerializer, LeadCreateSerializer,
    AssignAdvisorsSerializer, MoveStageSerializer,
    ActivityNoteSerializer, ActivityNoteCreateSerializer,
    StatusTransitionSerializer,
)
from apps.leads.services import LeadService
from apps.leads.selectors import (
    get_leads_for_tenant, get_lead_by_id, get_kanban_board, get_timeline,
)
from apps.common.mixins import TenantScopedViewMixin
from apps.common.permissions import IsAdvisorOrAbove, IsTeamLeadOrAbove, IsTenantEmployee


class LeadViewSet(TenantScopedViewMixin, viewsets.ModelViewSet):
    """
    FM-08: Lead CRUD, assignment, stage moves, timeline notes, conversion.
    BRU-01: all queries scoped to tenant via TenantScopedViewMixin.
    BRU-06: assign requires ≥1 advisor.
    BRU-16: create is idempotent — duplicate email returns existing lead.
    BRU-31: stage move atomically updates status + timeline + audit.
    BRU-08: private notes never returned to Customer Portal callers.

    A Lead IS a Prospect IS a Client IS a Former Client.
    Status controls the lifecycle stage — there is no separate client model.
    """

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'pipeline_stage', 'source', 'opted_out', 'is_suppressed', 'territory']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    ordering_fields = ['created_at', 'first_name', 'last_name', 'status', 'territory__name']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        advisor_filter = None
        if user.role == 'advisor':
            advisor_filter = user
        return get_leads_for_tenant(
            tenant=user.tenant,
            advisor=advisor_filter,
        )

    def get_serializer_class(self):
        if self.action == 'create':
            return LeadCreateSerializer
        return LeadSerializer

    def get_permissions(self):
        if self.action in ('assign', 'move_stage', 'destroy', 'convert'):
            return [IsAuthenticated(), IsTeamLeadOrAbove()]
        if self.action == 'timeline' and self.request.method == 'GET':
            return [IsAuthenticated(), IsTenantEmployee()]
        return [IsAuthenticated(), IsAdvisorOrAbove()]

    def perform_create(self, serializer):
        user = self.request.user
        lead = LeadService.create_lead(
            tenant=user.tenant,
            actor=user,
            **serializer.validated_data,
        )
        serializer.instance = lead

    @action(detail=True, methods=['post'], url_path='assign')
    def assign(self, request, pk=None):
        """FR-08.3 / BRU-06: assign advisors to a lead."""
        lead = get_lead_by_id(lead_id=pk, tenant=request.user.tenant)
        serializer = AssignAdvisorsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        LeadService.assign_advisors(
            lead=lead,
            advisor_ids=serializer.validated_data['advisor_ids'],
            actor=request.user,
        )
        return Response(LeadSerializer(lead).data)

    @action(detail=True, methods=['post'], url_path='move-stage')
    def move_stage(self, request, pk=None):
        """FM-18 / BRU-31: move lead to a new pipeline stage."""
        lead = get_lead_by_id(lead_id=pk, tenant=request.user.tenant)
        serializer = MoveStageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        LeadService.move_stage(
            lead=lead,
            new_stage=serializer.validated_data['stage'],
            position=serializer.validated_data.get('position', 0),
            actor=request.user,
        )
        lead.refresh_from_db()
        return Response(LeadSerializer(lead).data)

    @action(detail=True, methods=['post'], url_path='convert')
    def convert(self, request, pk=None):
        """
        FM-08: convert a lead/prospect to a client.
        Sets Lead.status='client' atomically. No separate Client record is created.
        """
        lead = get_lead_by_id(lead_id=pk, tenant=request.user.tenant)
        lead = LeadService.convert_to_client(lead=lead, actor=request.user)
        return Response(LeadSerializer(lead).data)

    @action(detail=True, methods=['get', 'post'], url_path='timeline')
    def timeline(self, request, pk=None):
        """FM-10: get or add activity timeline notes. BRU-08: private notes never shown on portal."""
        lead = get_lead_by_id(lead_id=pk, tenant=request.user.tenant)

        if request.method == 'GET':
            # BRU-08: Customer Portal callers never see private notes.
            # All Tenant CRM callers (employees) see all notes.
            include_private = request.user.user_type != 'customer'
            notes = get_timeline(tenant=request.user.tenant, lead=lead, include_private=include_private)
            return Response(ActivityNoteSerializer(notes, many=True).data)

        serializer = ActivityNoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        note = LeadService.add_note(
            tenant=request.user.tenant,
            lead=lead,
            author=request.user,
            **serializer.validated_data,
        )
        return Response(ActivityNoteSerializer(note).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], url_path='kanban')
    def kanban(self, request):
        """FM-18: return the kanban board for the tenant."""
        user = request.user
        advisor_filter = user if user.role == 'advisor' else None
        leads = get_kanban_board(tenant=user.tenant, advisor=advisor_filter)
        return Response(LeadSerializer(leads, many=True).data)

    @action(detail=True, methods=['post'], url_path='opt-out')
    def opt_out(self, request, pk=None):
        """BRU-07: mark lead as opted out of all automated communications."""
        lead = get_lead_by_id(lead_id=pk, tenant=request.user.tenant)
        LeadService.opt_out(lead=lead, actor=request.user)
        return Response({'status': 'opted_out'})
