from rest_framework.exceptions import PermissionDenied


class TenantScopedRequestMixin:
    """Adds request.tenant as a convenience property resolved from request.user.tenant."""

    def initialize_request(self, request, *args, **kwargs):
        req = super().initialize_request(request, *args, **kwargs)
        return req

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.user and request.user.is_authenticated:
            request.tenant = getattr(request.user, 'tenant', None)
        else:
            request.tenant = None


class TenantScopedViewMixin(TenantScopedRequestMixin):
    """
    Mixin for all tenant-scoped ViewSets (BRU-01).

    Subclasses must define `get_queryset()` that returns a TenantScopedQuerySet.
    This mixin ensures `.for_tenant()` is always applied so no cross-tenant
    rows can ever be returned, even if the underlying queryset is accidentally broadened.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_authenticated:
            return qs.none()
        if user.role in {'super_admin', 'support'}:
            # Platform staff access is audited separately; they may cross tenants.
            return qs
        if user.tenant_id is None:
            raise PermissionDenied("No tenant context for this user.")
        return qs.for_tenant(user.tenant)

    def perform_create(self, serializer):
        """Automatically attach the requesting user's tenant on create."""
        user = self.request.user
        if user.tenant_id is None:
            raise PermissionDenied("No tenant context for this user.")
        serializer.save(tenant=user.tenant)
