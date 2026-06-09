from rest_framework import serializers
from apps.users.models import CustomUser


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='get_full_name', read_only=True)

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'user_type', 'role', 'tenant', 'mfa_enabled', 'is_active', 'date_joined',
        ]
        read_only_fields = ['id', 'date_joined']


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'first_name', 'last_name', 'user_type', 'role', 'tenant']

    def validate_role(self, value):
        request = self.context.get('request')
        if request and value in CustomUser.PLATFORM_ROLES and request.user.role != 'super_admin':
            raise serializers.ValidationError("Only Super Admin can assign platform roles.")
        return value

    def validate(self, data):
        role = data.get('role', '')
        user_type = data.get('user_type', '')
        if role in CustomUser.PLATFORM_ROLES and user_type != CustomUser.TYPE_PLATFORM_STAFF:
            raise serializers.ValidationError(
                "Platform roles require user_type='platform_staff'."
            )
        if role in CustomUser.EMPLOYEE_ROLES and user_type != CustomUser.TYPE_TENANT_EMPLOYEE:
            raise serializers.ValidationError(
                "Employee roles require user_type='tenant_employee'."
            )
        return data

    def create(self, validated_data):
        return CustomUser.objects.create_user(**validated_data)


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value


class MFAStatusSerializer(serializers.Serializer):
    """Scaffold: MFA enrollment status for privileged roles (NFR-SEC-3)."""
    mfa_enabled = serializers.BooleanField(read_only=True)
    mfa_required = serializers.SerializerMethodField()

    def get_mfa_required(self, obj):
        return obj.role in {'super_admin', 'support', 'compliance_officer', 'tenant_admin'}
