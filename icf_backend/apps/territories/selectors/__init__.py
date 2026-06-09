from apps.territories.models import Territory, AdvisorTerritory


def get_territories_for_tenant(*, tenant, active_only=True):
    """BRU-01: always scoped to tenant."""
    qs = Territory.objects.filter(tenant=tenant).order_by('name')
    if active_only:
        qs = qs.filter(is_active=True)
    return qs


def get_territory_by_id(*, tenant, territory_id):
    """BRU-01: cross-checks tenant on lookup."""
    return Territory.objects.get(pk=territory_id, tenant=tenant)


def get_advisors_for_territory(*, territory):
    """Return the through-table rows for a territory, with advisor details."""
    return (
        AdvisorTerritory.objects
        .filter(territory=territory)
        .select_related('advisor', 'assigned_by')
        .order_by('advisor__last_name')
    )


def get_territories_for_advisor(*, advisor, tenant):
    """Return active territories assigned to a specific advisor within the tenant."""
    return (
        Territory.objects
        .filter(
            tenant=tenant,
            advisor_territories__advisor=advisor,
            is_active=True,
        )
        .distinct()
        .order_by('name')
    )
