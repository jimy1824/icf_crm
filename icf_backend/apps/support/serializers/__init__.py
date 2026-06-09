from rest_framework import serializers
from apps.support.models import SupportTicket, TicketComment


class TicketCommentSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = TicketComment
        fields = ['id', 'author', 'author_name', 'body', 'is_internal', 'created_at']
        read_only_fields = ['id', 'author', 'author_name', 'created_at']


class SupportTicketSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    assigned_to_name = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    tenant_name = serializers.SerializerMethodField()

    def get_assigned_to_name(self, obj):
        return obj.assigned_to.get_full_name() if obj.assigned_to_id else None

    def get_comment_count(self, obj):
        return obj.comments.count()

    def get_tenant_name(self, obj):
        if obj.tenant_id is None:
            return None
        name = getattr(obj.tenant, 'firm_name', None) or getattr(obj.tenant, 'name', None)
        return name or str(obj.tenant)

    class Meta:
        model = SupportTicket
        fields = [
            'id', 'subject', 'body', 'category', 'priority', 'status',
            'created_by', 'created_by_name', 'assigned_to', 'assigned_to_name',
            'tenant_name', 'comment_count', 'resolved_at', 'closed_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'created_by', 'created_by_name', 'assigned_to',
            'assigned_to_name', 'tenant_name', 'comment_count', 'resolved_at',
            'closed_at', 'created_at', 'updated_at',
        ]


class SupportTicketCreateSerializer(serializers.Serializer):
    subject = serializers.CharField(max_length=300)
    body = serializers.CharField()
    category = serializers.ChoiceField(
        choices=SupportTicket.CATEGORY_CHOICES,
        default=SupportTicket.CATEGORY_OTHER,
    )
    priority = serializers.ChoiceField(
        choices=SupportTicket.PRIORITY_CHOICES,
        default=SupportTicket.PRIORITY_NORMAL,
    )


class TicketStatusTransitionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=SupportTicket.STATUS_CHOICES)


class TicketAssignSerializer(serializers.Serializer):
    assignee_id = serializers.IntegerField()


class TicketCommentCreateSerializer(serializers.Serializer):
    body = serializers.CharField()
    is_internal = serializers.BooleanField(default=False)
