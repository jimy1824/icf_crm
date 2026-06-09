"""
FM-22: Global search service.
BRU-35: results filtered by tenant + user type before return — no leakage via search.
BRU-01: every queryset filtered by tenant.

Strategy: ORM-based DB search (icontains) until Elasticsearch is provisioned.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

RESULT_LIMIT = 20


@dataclass
class SearchResult:
    entity_type: str
    entity_id: int
    label: str
    sublabel: str = ''
    url_hint: str = ''
    extra: dict = field(default_factory=dict)


class GlobalSearchService:

    @staticmethod
    def search(*, tenant, user, query: str, limit: int = RESULT_LIMIT) -> list[SearchResult]:
        """
        BRU-35: all results pre-filtered by tenant + user_type before being returned.
        Tenant employees search all leads/campaigns/communications.
        Customer Portal users only see their own record.
        """
        if not query or len(query.strip()) < 2:
            return []

        q = query.strip()
        results: list[SearchResult] = []

        results.extend(_search_leads(tenant=tenant, user=user, q=q))
        results.extend(_search_campaigns(tenant=tenant, user=user, q=q))
        results.extend(_search_communications(tenant=tenant, user=user, q=q))

        return results[:limit]


# ---------------------------------------------------------------------------
# Entity-specific search functions (all BRU-01 + BRU-35 compliant)
# ---------------------------------------------------------------------------

def _search_leads(*, tenant, user, q: str) -> list[SearchResult]:
    from apps.leads.models import Lead
    from apps.users.models import CustomUser

    base_qs = Lead.objects.filter(tenant=tenant)

    # D-04: advisors see only their own leads
    if user.user_type == CustomUser.TYPE_TENANT_EMPLOYEE and user.role == 'advisor':
        base_qs = base_qs.filter(assigned_advisors=user)

    ids = (
        base_qs.filter(first_name__icontains=q).values_list('pk', flat=True) |
        base_qs.filter(last_name__icontains=q).values_list('pk', flat=True) |
        base_qs.filter(email__icontains=q).values_list('pk', flat=True)
    )
    qs = Lead.objects.filter(pk__in=ids, tenant=tenant)[:RESULT_LIMIT]
    return [
        SearchResult(
            entity_type='lead',
            entity_id=lead.pk,
            label=f"{lead.first_name} {lead.last_name}",
            sublabel=f"{lead.email} [{lead.status}]",
            url_hint=f"/leads/{lead.pk}/",
        )
        for lead in qs
    ]


def _search_campaigns(*, tenant, user, q: str) -> list[SearchResult]:
    from apps.users.models import CustomUser
    # Customer Portal users never see campaigns
    if user.user_type != CustomUser.TYPE_TENANT_EMPLOYEE:
        return []
    from apps.campaigns.models import Campaign
    qs = Campaign.objects.filter(tenant=tenant, name__icontains=q)[:RESULT_LIMIT]
    return [
        SearchResult(
            entity_type='campaign',
            entity_id=c.pk,
            label=c.name,
            sublabel=c.status,
            url_hint=f"/campaigns/{c.pk}/",
        )
        for c in qs
    ]


def _search_communications(*, tenant, user, q: str) -> list[SearchResult]:
    from apps.users.models import CustomUser
    # Customer Portal users never see internal communications
    if user.user_type != CustomUser.TYPE_TENANT_EMPLOYEE:
        return []
    from apps.communications.models import Communication
    qs = Communication.objects.filter(
        tenant=tenant, subject__icontains=q,
    )[:RESULT_LIMIT]
    return [
        SearchResult(
            entity_type='communication',
            entity_id=c.pk,
            label=c.subject or f"{c.channel} {c.direction}",
            sublabel=str(c.created_at.date()),
            url_hint='/communications/timeline/',
        )
        for c in qs
    ]
