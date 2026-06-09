from rest_framework.permissions import BasePermission
from apps.users.models import CustomUser, CustomerAccount


class IsPlatformStaff(BasePermission):
    """Super Admin, Support, or Compliance Officer — Super Panel only."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.user_type == CustomUser.TYPE_PLATFORM_STAFF
        )


class IsSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == CustomUser.ROLE_SUPER_ADMIN
        )


class IsSupport(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in {CustomUser.ROLE_SUPER_ADMIN, CustomUser.ROLE_SUPPORT}
            and request.user.user_type == CustomUser.TYPE_PLATFORM_STAFF
        )


class IsComplianceOfficer(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in {CustomUser.ROLE_SUPER_ADMIN, CustomUser.ROLE_COMPLIANCE}
        )


class IsTenantEmployee(BasePermission):
    """Any authenticated user that is a tenant employee (Tenant CRM users)."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.user_type == CustomUser.TYPE_TENANT_EMPLOYEE
            and request.user.tenant_id is not None
        )


class IsTenantAdmin(BasePermission):
    """Tenant Admin only — does NOT include platform staff."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role == CustomUser.ROLE_TENANT_ADMIN
            and request.user.user_type == CustomUser.TYPE_TENANT_EMPLOYEE
        )


class IsTenantAdminOrAbove(BasePermission):
    """Tenant Admin, or Super Admin (cross-platform management only)."""

    ALLOWED_ROLES = {CustomUser.ROLE_TENANT_ADMIN, CustomUser.ROLE_SUPER_ADMIN}

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in self.ALLOWED_ROLES
        )


class IsTenantMember(BasePermission):
    """Any authenticated user that belongs to a tenant."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.tenant_id is not None
        )


class IsAdvisorOrAbove(BasePermission):
    """Advisor, Team Lead, or Tenant Admin — all tenant employees."""

    ALLOWED = {CustomUser.ROLE_ADVISOR, CustomUser.ROLE_TEAM_LEAD, CustomUser.ROLE_TENANT_ADMIN}

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in self.ALLOWED
            and request.user.user_type == CustomUser.TYPE_TENANT_EMPLOYEE
        )


class IsTeamLeadOrAbove(BasePermission):
    """Team Lead or Tenant Admin."""

    ALLOWED = {CustomUser.ROLE_TEAM_LEAD, CustomUser.ROLE_TENANT_ADMIN}

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in self.ALLOWED
            and request.user.user_type == CustomUser.TYPE_TENANT_EMPLOYEE
        )


class IsCustomerPortalUser(BasePermission):
    """
    Customer Portal permission — request.user must be a CustomerAccount instance.
    Works in conjunction with CustomerJWTAuthentication which resolves portal
    tokens to CustomerAccount (never CustomUser).
    BRU-01: all portal views additionally scope queries to request.user.lead.
    """

    def has_permission(self, request, view):
        return bool(
            request.user
            and isinstance(request.user, CustomerAccount)
            and request.user.is_active
        )
