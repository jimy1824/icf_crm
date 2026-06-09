from apps.communications.models import (
    CallLog,
    Communication,
    ConsentPreference,
    DeliverabilityEvent,
    MailboxConnection,
    Meeting,
    SuppressionRecord,
    TriggerDomain,
)


# ---------------------------------------------------------------------------
# MailboxConnection
# ---------------------------------------------------------------------------

def get_mailbox_connection(*, tenant, advisor, provider) -> MailboxConnection | None:
    return MailboxConnection.objects.filter(
        tenant=tenant, advisor=advisor, provider=provider,
    ).first()


def get_active_mailbox_connections(*, tenant):
    return MailboxConnection.objects.filter(
        tenant=tenant, status=MailboxConnection.STATUS_ACTIVE,
    ).select_related('advisor')


def get_expiring_connections(*, before_dt):
    """BRU-05: connections whose token expires before the given datetime."""
    return MailboxConnection.objects.filter(
        status=MailboxConnection.STATUS_ACTIVE,
        token_expires_at__lte=before_dt,
    ).select_related('tenant', 'advisor')


# ---------------------------------------------------------------------------
# Communication
# ---------------------------------------------------------------------------

def get_communication_by_external_id(*, external_id) -> Communication | None:
    return Communication.objects.filter(external_id=external_id).first()


def get_timeline_for_lead(*, tenant, lead):
    return Communication.objects.filter(tenant=tenant, lead=lead).order_by('-created_at')


def communication_exists_by_external_id(*, external_id) -> bool:
    return Communication.objects.filter(external_id=external_id).exists()


def get_communications_for_tenant(*, tenant, channel=None, direction=None, lead=None,
                                   date_from=None, date_to=None):
    qs = Communication.objects.filter(tenant=tenant).select_related(
        'lead', 'sent_by'
    ).prefetch_related('call_log').order_by('-created_at')
    if channel:
        qs = qs.filter(channel=channel)
    if direction:
        qs = qs.filter(direction=direction)
    if lead:
        qs = qs.filter(lead=lead)
    if date_from:
        qs = qs.filter(created_at__date__gte=date_from)
    if date_to:
        qs = qs.filter(created_at__date__lte=date_to)
    return qs


def get_unread_replies(*, tenant):
    return Communication.objects.filter(
        tenant=tenant, direction=Communication.DIRECTION_INBOUND, is_reply=True,
    ).select_related('lead')


# ---------------------------------------------------------------------------
# CallLog
# ---------------------------------------------------------------------------

def get_call_log_by_id(*, tenant, pk) -> CallLog | None:
    return CallLog.objects.filter(tenant=tenant, pk=pk).select_related('communication').first()


def get_call_logs_for_tenant(*, tenant, outcome=None):
    qs = CallLog.objects.filter(tenant=tenant).select_related(
        'communication__lead',
    )
    if outcome:
        qs = qs.filter(outcome=outcome)
    return qs


# ---------------------------------------------------------------------------
# Meeting
# ---------------------------------------------------------------------------

def get_meeting_by_id(*, tenant, pk) -> Meeting | None:
    return Meeting.objects.filter(tenant=tenant, pk=pk).select_related(
        'advisor', 'lead',
    ).first()


def get_meetings_for_advisor(*, tenant, advisor, upcoming_only=False):
    from django.utils import timezone
    qs = Meeting.objects.filter(tenant=tenant, advisor=advisor).select_related('lead')
    if upcoming_only:
        qs = qs.filter(scheduled_at__gte=timezone.now())
    return qs


def get_pending_reminders(*, before_dt):
    """BRU-24: meetings needing a reminder dispatch."""
    return Meeting.objects.filter(
        reminder_sent=False,
        scheduled_at__lte=before_dt,
    ).select_related('tenant', 'advisor', 'lead')


# ---------------------------------------------------------------------------
# SuppressionRecord
# ---------------------------------------------------------------------------

def is_email_suppressed(*, tenant, email: str) -> bool:
    return SuppressionRecord.objects.filter(
        tenant=tenant,
        email__iexact=email,
        channel__in=[SuppressionRecord.CHANNEL_EMAIL, SuppressionRecord.CHANNEL_ALL],
    ).exists()


def is_phone_suppressed(*, tenant, phone: str) -> bool:
    return SuppressionRecord.objects.filter(
        tenant=tenant,
        phone=phone,
        channel__in=[SuppressionRecord.CHANNEL_SMS, SuppressionRecord.CHANNEL_ALL],
    ).exists()


def get_suppressions_for_tenant(*, tenant, channel=None):
    qs = SuppressionRecord.objects.filter(tenant=tenant)
    if channel:
        qs = qs.filter(channel=channel)
    return qs


# ---------------------------------------------------------------------------
# ConsentPreference
# ---------------------------------------------------------------------------

def get_latest_consent(*, tenant, channel, purpose, lead=None) -> ConsentPreference | None:
    qs = ConsentPreference.objects.filter(tenant=tenant, channel=channel, purpose=purpose)
    if lead:
        qs = qs.filter(lead=lead)
    return qs.order_by('-created_at').first()


def get_consent_history(*, tenant, lead=None):
    qs = ConsentPreference.objects.filter(tenant=tenant).order_by('-created_at')
    if lead:
        qs = qs.filter(lead=lead)
    return qs


# ---------------------------------------------------------------------------
# DeliverabilityEvent
# ---------------------------------------------------------------------------

def get_unprocessed_events(*, tenant):
    return DeliverabilityEvent.objects.filter(tenant=tenant, processed=False)


# ---------------------------------------------------------------------------
# TriggerDomain
# ---------------------------------------------------------------------------

def get_trigger_domains(*, tenant, active_only=True):
    qs = TriggerDomain.objects.filter(tenant=tenant)
    if active_only:
        qs = qs.filter(is_active=True)
    return qs
