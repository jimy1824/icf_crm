from rest_framework import serializers

from apps.documents.models import Document


class DocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()
    verified_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'doc_type', 'kyc_status',
            'storage_ref', 'version',
            'uploaded_by_name', 'uploaded_at',
            'verified_by_name', 'verified_at',
            'is_under_legal_hold', 'consent_captured', 'retain_until',
        ]
        read_only_fields = [
            'id', 'kyc_status', 'version',
            'uploaded_by_name', 'uploaded_at',
            'verified_by_name', 'verified_at',
            'is_under_legal_hold',
        ]

    def get_uploaded_by_name(self, obj) -> str:
        if obj.uploaded_by:
            return f"{obj.uploaded_by.first_name} {obj.uploaded_by.last_name}".strip()
        return ''

    def get_verified_by_name(self, obj) -> str:
        if obj.verified_by:
            return f"{obj.verified_by.first_name} {obj.verified_by.last_name}".strip()
        return ''


class DocumentUploadSerializer(serializers.Serializer):
    doc_type = serializers.ChoiceField(choices=Document.TYPE_CHOICES)
    storage_ref = serializers.CharField(max_length=500)
    filename = serializers.CharField(max_length=255, required=False, default='')
    consent_captured = serializers.BooleanField(default=False)
    retain_until = serializers.DateField(required=False, allow_null=True, default=None)


class DocumentVerifySerializer(serializers.Serializer):
    """Used for both verify and reject actions."""
    reason = serializers.CharField(required=False, default='')
