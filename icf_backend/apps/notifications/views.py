from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from apps.notifications.services import NotificationService


class NotificationListView(APIView):
    """FM-14: list own notifications (BRU-01: tenant + recipient scoped)."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(
            tenant=request.user.tenant,
            recipient=request.user,
        )
        unread_only = request.query_params.get('unread')
        if unread_only:
            qs = qs.filter(is_read=False)
        serializer = NotificationSerializer(qs, many=True)
        return Response({
            'results': serializer.data,
            'unread_count': NotificationService.unread_count(
                tenant=request.user.tenant, recipient=request.user,
            ),
        })


class NotificationMarkReadView(APIView):
    """FM-14: mark a single notification as read."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(
                pk=pk, tenant=request.user.tenant, recipient=request.user,
            )
        except Notification.DoesNotExist:
            return Response({'detail': 'Not found.'}, status=status.HTTP_404_NOT_FOUND)
        NotificationService.mark_read(notification=notification)
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadView(APIView):
    """FM-14: mark all of the user's notifications as read."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = NotificationService.mark_all_read(
            tenant=request.user.tenant, recipient=request.user,
        )
        return Response({'marked_read': count})


class NotificationUnreadCountView(APIView):
    """Lightweight polling endpoint — returns only the unread count."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = NotificationService.unread_count(
            tenant=request.user.tenant, recipient=request.user,
        )
        return Response({'unread_count': count})
