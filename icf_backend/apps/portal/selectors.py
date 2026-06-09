"""
Portal selectors — query logic for customer portal endpoints.
Every selector MUST be scoped to lead AND tenant (BRU-01).
BRU-08: is_private=True content is NEVER exposed.
"""

from apps.communications.models import Communication, Meeting
from apps.documents.models import Document
from apps.financials.models import FinancialGoal, FinancialProfile
from apps.leads.models import ActivityNote, ConsentRecord, Household, HouseholdMembership
from apps.notifications.models import Notification


def get_portal_financial_profile(*, lead):
    """Return the lead's financial profile, or None if not yet created."""
    try:
        return FinancialProfile.objects.prefetch_related(
            'accounts', 'insurance_policies'
        ).get(lead=lead, tenant=lead.tenant)
    except FinancialProfile.DoesNotExist:
        return None


def get_portal_goals(*, lead):
    """Return all financial goals for the lead (BRU-01: tenant+lead scoped)."""
    return FinancialGoal.objects.filter(
        lead=lead,
        tenant=lead.tenant,
    ).prefetch_related('milestones').order_by('target_date')


def get_portal_goal(*, lead, goal_pk):
    """Return a single goal with milestones, scoped to this lead."""
    from django.shortcuts import get_object_or_404
    return get_object_or_404(
        FinancialGoal.objects.prefetch_related('milestones'),
        pk=goal_pk,
        lead=lead,
        tenant=lead.tenant,
    )


def get_portal_documents(*, lead):
    """Return all documents for the lead. BRU-01: tenant+lead scoped."""
    return Document.objects.filter(
        lead=lead,
        tenant=lead.tenant,
    ).order_by('-uploaded_at')


def get_portal_document(*, lead, doc_pk):
    """Return a single document scoped to this lead."""
    from django.shortcuts import get_object_or_404
    return get_object_or_404(
        Document,
        pk=doc_pk,
        lead=lead,
        tenant=lead.tenant,
    )


def get_portal_meetings(*, lead):
    """Return all meetings for the lead, newest first. BRU-01 scoped."""
    return Meeting.objects.filter(
        lead=lead,
        tenant=lead.tenant,
    ).select_related('advisor').order_by('-scheduled_at')


def get_portal_meeting(*, lead, meeting_pk):
    """Return a single meeting scoped to this lead."""
    from django.shortcuts import get_object_or_404
    return get_object_or_404(
        Meeting.objects.select_related('advisor'),
        pk=meeting_pk,
        lead=lead,
        tenant=lead.tenant,
    )


def get_portal_communications(*, lead, channel=None):
    """
    Return communications for the lead.
    BRU-08: Communication records are all channel-level events visible to the lead.
    Private advisor notes live on ActivityNote (separate model), never here.
    """
    qs = Communication.objects.filter(
        lead=lead,
        tenant=lead.tenant,
    ).order_by('-created_at')
    if channel:
        qs = qs.filter(channel=channel)
    return qs


def get_portal_notifications(*, customer_account):
    """
    Return notifications for the customer account's lead.
    Notifications in this system are linked to CustomUser recipients via FK;
    for portal users we scope to entity_type='Lead' and entity_id=lead.pk.
    """
    return Notification.objects.filter(
        tenant=customer_account.tenant,
        entity_type='Lead',
        entity_id=str(customer_account.lead.pk),
    ).order_by('-created_at')


def get_portal_consent_records(*, lead):
    """Return all consent records for this lead (BRU-07/15). BRU-01 scoped."""
    return ConsentRecord.objects.filter(
        lead=lead,
        tenant=lead.tenant,
    ).order_by('-recorded_at')


def get_portal_household(*, lead):
    """
    Return household for the lead if they belong to one (BRU-28).
    Returns None if lead has no household.
    """
    if not lead.household_id:
        return None
    try:
        return Household.objects.prefetch_related(
            'members',
            'memberships',
        ).get(pk=lead.household_id, tenant=lead.tenant)
    except Household.DoesNotExist:
        return None


def get_portal_advisors(*, lead):
    """Return assigned advisors for the lead (public info only — no internal notes)."""
    return lead.assigned_advisors.filter(is_active=True).only(
        'id', 'first_name', 'last_name', 'email'
    )
