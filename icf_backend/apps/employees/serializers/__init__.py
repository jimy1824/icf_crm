from rest_framework import serializers
from apps.employees.models import Employee, Role, EmployeeRole, Permission
from apps.users.serializers import UserSerializer


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'codename', 'description']
        read_only_fields = ['id']


class RoleSerializer(serializers.ModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = ['id', 'slug', 'name', 'permissions']
        read_only_fields = ['id']


class EmployeeRoleSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)

    class Meta:
        model = EmployeeRole
        fields = ['id', 'role', 'assigned_at']
        read_only_fields = ['id', 'assigned_at']


class EmployeeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    roles = RoleSerializer(many=True, read_only=True)
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    primary_role = serializers.CharField(source='get_primary_role_slug', read_only=True)

    class Meta:
        model = Employee
        fields = [
            'id', 'full_name', 'email', 'user', 'roles', 'primary_role',
            'job_title', 'department', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class EmployeeCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    role_slug = serializers.ChoiceField(choices=list(Role.CORE_SLUGS))
    job_title = serializers.CharField(max_length=150, required=False, default='')


class AssignRoleSerializer(serializers.Serializer):
    role_slug = serializers.ChoiceField(choices=list(Role.CORE_SLUGS))
