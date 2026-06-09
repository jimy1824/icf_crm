from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.support.models import SupportTicket, TicketComment
from apps.support.serializers import (
    SupportTicketSerializer,
    SupportTicketCreateSerializer,
    TicketStatusTransitionSerializer,
    TicketAssignSerializer,
    TicketCommentSerializer,
    TicketCommentCreateSerializer,
)
from apps.support.services import SupportService


def _drf(exc: DjangoValidationError):
    from rest_framework.exceptions import ValidationError
    return ValidationError(exc.messages if hasattr(exc, 'messages') else str(exc))


def _is_platform_staff(user):
    return user.role in ('super_admin', 'support')


def _get_ticket_for_user(pk, user):
    """
    Fetch a ticket visible to the given user.
    Platform staff can access any ticket.
    Tenant employees are scoped to their own tenant.
    """
    try:
        if _is_platform_staff(user):
            return SupportTicket.objects.select_related(
                'created_by', 'assigned_to', 'tenant',
            ).prefetch_related('comments').get(pk=pk)
        return SupportTicket.objects.select_related(
            'created_by', 'assigned_to', 'tenant',
        ).prefetch_related('comments').get(pk=pk, tenant=user.tenant)
    except SupportTicket.DoesNotExist:
        return None


class SupportTicketListView(APIView):
    """FM-04: list all tickets for the tenant; create a new ticket."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Q

        # Super panel staff can see tickets across all tenants (or filter by tenant_id)
        is_staff = request.user.role in ('super_admin', 'support')
        tenant_id_filter = request.query_params.get('tenant_id')

        if is_staff and tenant_id_filter:
            qs = SupportTicket.objects.filter(tenant_id=tenant_id_filter)
        elif is_staff:
            # See all tenants' tickets
            qs = SupportTicket.objects.all()
        else:
            qs = SupportTicket.objects.filter(tenant=request.user.tenant)

        qs = qs.select_related('created_by', 'assigned_to', 'tenant').prefetch_related('comments')

        # BRU-35: non-admin users only see their own tickets
        if request.user.role not in ('super_admin', 'support', 'tenant_admin'):
            qs = qs.filter(created_by=request.user)

        status_filter = request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        category_filter = request.query_params.get('category')
        if category_filter:
            qs = qs.filter(category=category_filter)

        priority_filter = request.query_params.get('priority')
        if priority_filter:
            qs = qs.filter(priority=priority_filter)

        assigned_to_filter = request.query_params.get('assigned_to')
        if assigned_to_filter == 'me':
            qs = qs.filter(assigned_to=request.user)
        elif assigned_to_filter == 'unassigned':
            qs = qs.filter(assigned_to__isnull=True)
        elif assigned_to_filter:
            qs = qs.filter(assigned_to_id=assigned_to_filter)

        date_from = request.query_params.get('date_from')
        if date_from:
            qs = qs.filter(created_at__date__gte=date_from)

        date_to = request.query_params.get('date_to')
        if date_to:
            qs = qs.filter(created_at__date__lte=date_to)

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(subject__icontains=search)
                | Q(body__icontains=search)
                | Q(id__icontains=search)
                | Q(tenant__firm_name__icontains=search)
            )

        # Ordering
        ordering = request.query_params.get('ordering', '-created_at')
        allowed_orderings = {
            'id', '-id', 'priority', '-priority', 'status', '-status',
            'created_at', '-created_at', 'updated_at', '-updated_at',
        }
        if ordering not in allowed_orderings:
            ordering = '-created_at'
        qs = qs.order_by(ordering)

        # Pagination
        try:
            page = max(1, int(request.query_params.get('page', 1)))
            page_size = min(200, max(1, int(request.query_params.get('page_size', 20))))
        except (ValueError, TypeError):
            page, page_size = 1, 20

        total = qs.count()
        offset = (page - 1) * page_size
        qs = qs[offset:offset + page_size]

        serializer = SupportTicketSerializer(qs, many=True)
        return Response({'count': total, 'results': serializer.data})

    def post(self, request):
        serializer = SupportTicketCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        try:
            ticket = SupportService.create_ticket(
                tenant=request.user.tenant,
                created_by=request.user,
                **d,
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(SupportTicketSerializer(ticket).data, status=status.HTTP_201_CREATED)


class SupportTicketDetailView(APIView):
    """FM-04: retrieve a single ticket."""
    permission_classes = [IsAuthenticated]

    def _get_ticket(self, request, pk):
        ticket = _get_ticket_for_user(pk, request.user)
        if not ticket:
            return None
        # Non-admin tenant employees can only see their own tickets
        if request.user.role not in ('super_admin', 'support', 'tenant_admin'):
            if ticket.created_by_id != request.user.pk:
                return None
        return ticket

    def get(self, request, pk):
        ticket = self._get_ticket(request, pk)
        if not ticket:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(SupportTicketSerializer(ticket).data)


class TicketStatusView(APIView):
    """FM-04: transition ticket status. Support staff or tenant admin."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if request.user.role not in ('super_admin', 'support', 'tenant_admin'):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        ticket = _get_ticket_for_user(pk, request.user)
        if not ticket:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = TicketStatusTransitionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            ticket = SupportService.transition_status(
                ticket=ticket,
                new_status=serializer.validated_data['status'],
                actor=request.user,
            )
        except DjangoValidationError as exc:
            raise _drf(exc)
        return Response(SupportTicketSerializer(ticket).data)


class TicketAssignView(APIView):
    """FM-04: assign ticket to a support user. Platform staff only."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        if not _is_platform_staff(request.user):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        ticket = _get_ticket_for_user(pk, request.user)
        if not ticket:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = TicketAssignSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        from apps.users.models import CustomUser
        try:
            assignee = CustomUser.objects.get(
                pk=serializer.validated_data['assignee_id'],
            )
        except CustomUser.DoesNotExist:
            return Response({'detail': 'Assignee not found.'}, status=status.HTTP_400_BAD_REQUEST)
        ticket = SupportService.assign_ticket(
            ticket=ticket, assignee=assignee, actor=request.user,
        )
        return Response(SupportTicketSerializer(ticket).data)


class TicketCommentListView(APIView):
    """FM-04: list and create comments on a ticket."""
    permission_classes = [IsAuthenticated]

    def _get_ticket(self, request, pk):
        ticket = _get_ticket_for_user(pk, request.user)
        if not ticket:
            return None
        # Non-admin tenant employees can only see their own tickets
        if request.user.role not in ('super_admin', 'support', 'tenant_admin'):
            if ticket.created_by_id != request.user.pk:
                return None
        return ticket

    def get(self, request, pk):
        ticket = self._get_ticket(request, pk)
        if not ticket:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        qs = ticket.comments.select_related('author')
        # Non-staff cannot see internal notes
        if request.user.role not in ('super_admin', 'support'):
            qs = qs.filter(is_internal=False)
        return Response(TicketCommentSerializer(qs, many=True).data)

    def post(self, request, pk):
        ticket = self._get_ticket(request, pk)
        if not ticket:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        serializer = TicketCommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        # Only staff can post internal notes
        is_internal = d.get('is_internal', False)
        if is_internal and request.user.role not in ('super_admin', 'support'):
            is_internal = False
        comment = SupportService.add_comment(
            ticket=ticket, author=request.user, body=d['body'], is_internal=is_internal,
        )
        return Response(TicketCommentSerializer(comment).data, status=status.HTTP_201_CREATED)


class TicketStatsView(APIView):
    """
    GET /support/tickets/stats/
    Returns counts per status + resolved-this-month, scoped to tenant.
    BRU-01: always filtered to request.user.tenant.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.db.models import Count, Q

        is_staff = request.user.role in ('super_admin', 'support')
        tenant_id_filter = request.query_params.get('tenant_id')

        if is_staff and tenant_id_filter:
            base_qs = SupportTicket.objects.filter(tenant_id=tenant_id_filter)
        elif is_staff:
            base_qs = SupportTicket.objects.all()
        else:
            base_qs = SupportTicket.objects.filter(tenant=request.user.tenant)

        # Non-admin only count their own
        if request.user.role not in ('super_admin', 'support', 'tenant_admin'):
            base_qs = base_qs.filter(created_by=request.user)

        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        counts = base_qs.aggregate(
            total=Count('id'),
            open=Count('id', filter=Q(status='open')),
            in_progress=Count('id', filter=Q(status='in_progress')),
            waiting=Count('id', filter=Q(status='waiting_on_customer')),
            resolved=Count('id', filter=Q(status='resolved')),
            closed=Count('id', filter=Q(status='closed')),
            resolved_this_month=Count('id', filter=Q(
                status='resolved', resolved_at__gte=month_start,
            )),
        )
        return Response(counts)


class TicketUpdateView(APIView):
    """
    PATCH /support/tickets/<pk>/update/
    Updates subject, body, priority, category. Platform staff access any ticket.
    """
    permission_classes = [IsAuthenticated]

    def _get_ticket(self, request, pk):
        ticket = _get_ticket_for_user(pk, request.user)
        if not ticket:
            return None
        # Non-admin tenant employees can only edit their own tickets
        if request.user.role not in ('super_admin', 'support', 'tenant_admin'):
            if ticket.created_by_id != request.user.pk:
                return None
        return ticket

    def patch(self, request, pk):
        ticket = self._get_ticket(request, pk)
        if not ticket:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        if ticket.status == SupportTicket.STATUS_CLOSED:
            return Response({'detail': 'Closed tickets cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST)
        allowed = {'subject', 'body', 'priority', 'category'}
        for field in allowed:
            if field in request.data:
                setattr(ticket, field, request.data[field])
        ticket.save(update_fields=list(allowed & set(request.data.keys())) + ['updated_at'])
        return Response(SupportTicketSerializer(ticket).data)


class SupportStaffListView(APIView):
    """
    GET /support/staff/
    Returns all platform staff (super_admin + support roles) available for ticket assignment.
    Only accessible by platform staff themselves.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_platform_staff(request.user):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        from apps.users.models import CustomUser
        staff = CustomUser.objects.filter(
            user_type=CustomUser.TYPE_PLATFORM_STAFF,
            is_active=True,
        ).order_by('first_name', 'last_name').values('id', 'first_name', 'last_name', 'email', 'role')
        data = [
            {
                'id': u['id'],
                'name': f"{u['first_name']} {u['last_name']}".strip() or u['email'],
                'email': u['email'],
                'role': u['role'],
            }
            for u in staff
        ]
        return Response(data)


# ── Platform Staff Management (Super Admin only) ────────────────────────────

class PlatformStaffListView(APIView):
    """
    GET  /support/platform-staff/  — paginated list of ICF internal staff.
    POST /support/platform-staff/  — invite/create a new staff member.
    Super Admin only.
    """
    permission_classes = [IsAuthenticated]

    def _require_super_admin(self, user):
        return user.role == 'super_admin'

    def get(self, request):
        if not self._require_super_admin(request.user):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        from django.db.models import Q
        from apps.users.models import CustomUser

        qs = CustomUser.objects.filter(user_type=CustomUser.TYPE_PLATFORM_STAFF)

        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(email__icontains=search)
            )

        role_filter = request.query_params.get('role', '').strip()
        if role_filter:
            qs = qs.filter(role=role_filter)

        is_active_param = request.query_params.get('is_active', '').strip()
        if is_active_param in ('true', 'True', '1'):
            qs = qs.filter(is_active=True)
        elif is_active_param in ('false', 'False', '0'):
            qs = qs.filter(is_active=False)

        ordering = request.query_params.get('ordering', '-date_joined')
        allowed = {'date_joined', '-date_joined', 'first_name', '-first_name', 'last_name', '-last_name', 'email', '-email', 'role', '-role'}
        if ordering not in allowed:
            ordering = '-date_joined'
        qs = qs.order_by(ordering)

        try:
            page = max(1, int(request.query_params.get('page', 1)))
            page_size = min(100, max(1, int(request.query_params.get('page_size', 20))))
        except (ValueError, TypeError):
            page, page_size = 1, 20

        total = qs.count()
        offset = (page - 1) * page_size
        page_qs = qs[offset:offset + page_size]

        data = [
            {
                'id': u.id,
                'email': u.email,
                'first_name': u.first_name,
                'last_name': u.last_name,
                'full_name': u.get_full_name() or u.email,
                'role': u.role,
                'is_active': u.is_active,
                'mfa_enabled': u.mfa_enabled,
                'date_joined': u.date_joined,
            }
            for u in page_qs
        ]
        return Response({'count': total, 'results': data})

    def post(self, request):
        if not self._require_super_admin(request.user):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        from apps.users.models import CustomUser
        from apps.audit.services import AuditService

        required = ['email', 'first_name', 'last_name', 'role', 'password']
        for field in required:
            if not request.data.get(field):
                return Response({'detail': f'{field} is required.'}, status=status.HTTP_400_BAD_REQUEST)

        role = request.data['role']
        if role not in {'super_admin', 'support', 'compliance_officer'}:
            return Response({'detail': 'Invalid role for platform staff.'}, status=status.HTTP_400_BAD_REQUEST)

        email = request.data['email'].strip().lower()
        if CustomUser.objects.filter(email=email).exists():
            return Response({'detail': 'A user with this email already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        user = CustomUser.objects.create_user(
            email=email,
            password=request.data['password'],
            first_name=request.data['first_name'].strip(),
            last_name=request.data['last_name'].strip(),
            user_type=CustomUser.TYPE_PLATFORM_STAFF,
            role=role,
        )
        AuditService.log_from_request(
            request,
            action='platform_staff.create',
            entity_type='CustomUser',
            entity_id=user.pk,
            after_state={'email': user.email, 'role': user.role},
        )
        return Response({
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name() or user.email,
            'role': user.role,
            'is_active': user.is_active,
            'mfa_enabled': user.mfa_enabled,
            'date_joined': user.date_joined,
        }, status=status.HTTP_201_CREATED)


class PlatformStaffDetailView(APIView):
    """
    GET   /support/platform-staff/<pk>/  — retrieve a staff member.
    PATCH /support/platform-staff/<pk>/  — update name/role.
    Super Admin only (read available to all platform staff).
    """
    permission_classes = [IsAuthenticated]

    def _get_staff(self, pk):
        from apps.users.models import CustomUser
        try:
            return CustomUser.objects.get(pk=pk, user_type=CustomUser.TYPE_PLATFORM_STAFF)
        except CustomUser.DoesNotExist:
            return None

    def get(self, request, pk):
        if not _is_platform_staff(request.user):
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        user = self._get_staff(pk)
        if not user:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response({
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name() or user.email,
            'role': user.role,
            'is_active': user.is_active,
            'mfa_enabled': user.mfa_enabled,
            'date_joined': user.date_joined,
        })

    def patch(self, request, pk):
        if request.user.role != 'super_admin':
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        from apps.audit.services import AuditService
        user = self._get_staff(pk)
        if not user:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        before = {'first_name': user.first_name, 'last_name': user.last_name, 'role': user.role}
        updated_fields = []

        for field in ('first_name', 'last_name'):
            if field in request.data:
                setattr(user, field, request.data[field].strip())
                updated_fields.append(field)

        if 'role' in request.data:
            new_role = request.data['role']
            if new_role not in {'super_admin', 'support', 'compliance_officer'}:
                return Response({'detail': 'Invalid role.'}, status=status.HTTP_400_BAD_REQUEST)
            user.role = new_role
            updated_fields.append('role')

        if updated_fields:
            user.save(update_fields=updated_fields)
            AuditService.log_from_request(
                request,
                action='platform_staff.update',
                entity_type='CustomUser',
                entity_id=user.pk,
                before_state=before,
                after_state={f: getattr(user, f) for f in updated_fields},
            )

        return Response({
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'full_name': user.get_full_name() or user.email,
            'role': user.role,
            'is_active': user.is_active,
            'mfa_enabled': user.mfa_enabled,
            'date_joined': user.date_joined,
        })


class PlatformStaffDeactivateView(APIView):
    """
    POST /support/platform-staff/<pk>/deactivate/
    POST /support/platform-staff/<pk>/activate/
    Super Admin only. Cannot deactivate yourself.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, action_type):
        if request.user.role != 'super_admin':
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        from apps.users.models import CustomUser
        from apps.audit.services import AuditService

        try:
            target = CustomUser.objects.get(pk=pk, user_type=CustomUser.TYPE_PLATFORM_STAFF)
        except CustomUser.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)

        if action_type == 'deactivate' and target.pk == request.user.pk:
            return Response({'detail': 'You cannot deactivate your own account.'}, status=status.HTTP_400_BAD_REQUEST)

        before = {'is_active': target.is_active}
        target.is_active = (action_type == 'activate')
        target.save(update_fields=['is_active'])

        AuditService.log_from_request(
            request,
            action=f'platform_staff.{action_type}',
            entity_type='CustomUser',
            entity_id=target.pk,
            before_state=before,
            after_state={'is_active': target.is_active},
        )
        return Response({'status': action_type + 'd', 'is_active': target.is_active})


class PlatformStaffStatsView(APIView):
    """
    GET /support/platform-staff/stats/
    Returns summary counts for ICF internal staff. Super Admin only.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'super_admin':
            return Response({'detail': 'Forbidden.'}, status=status.HTTP_403_FORBIDDEN)
        from django.db.models import Count, Q
        from apps.users.models import CustomUser

        counts = CustomUser.objects.filter(
            user_type=CustomUser.TYPE_PLATFORM_STAFF
        ).aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            inactive=Count('id', filter=Q(is_active=False)),
            super_admins=Count('id', filter=Q(role='super_admin')),
            support_count=Count('id', filter=Q(role='support')),
            compliance_count=Count('id', filter=Q(role='compliance_officer')),
        )
        return Response(counts)
