"""
FM-08: Lead — the single business entity for all customer-facing lifecycle stages.

A person is ONE entity from first capture through their entire relationship.
Status controls the lifecycle stage:

  lead → prospect → client → former_client

Other terminal/special statuses: lost, deceased.

The `Household` and `ConsentRecord` models live here because they are directly
tied to leads/clients — there is no separate clients app.
"""

from django.conf import settings
from django.db import models
from apps.common.models import BaseModel, TenantBaseModel


# ---------------------------------------------------------------------------
# Lead (FM-08) — single entity for all lifecycle stages
# ---------------------------------------------------------------------------

class Lead(TenantBaseModel):
    # --- Sources (FR-08.1, BRU-02) ---
    SOURCE_WEB_FORM = 'web_form'
    SOURCE_MANUAL = 'manual'
    SOURCE_API_IMPORT = 'api_import'
    SOURCE_EMAIL_TRIGGER = 'email_trigger'
    SOURCE_CHOICES = [
        (SOURCE_WEB_FORM, 'Web Form'),
        (SOURCE_MANUAL, 'Manual'),
        (SOURCE_API_IMPORT, 'API Import'),
        (SOURCE_EMAIL_TRIGGER, 'Email Trigger'),
    ]

    # --- Lifecycle statuses (single entity, status controls the stage) ---
    STATUS_LEAD = 'lead'
    STATUS_PROSPECT = 'prospect'
    STATUS_CLIENT = 'client'
    STATUS_FORMER_CLIENT = 'former_client'
    STATUS_LOST = 'lost'
    STATUS_DECEASED = 'deceased'
    STATUS_CHOICES = [
        (STATUS_LEAD, 'Lead'),
        (STATUS_PROSPECT, 'Prospect'),
        (STATUS_CLIENT, 'Client'),
        (STATUS_FORMER_CLIENT, 'Former Client'),
        (STATUS_LOST, 'Lost'),
        (STATUS_DECEASED, 'Deceased'),
    ]

    # Statuses where the full financial relationship is active
    ACTIVE_CLIENT_STATUSES = {STATUS_CLIENT}
    # Statuses visible in the "Leads" view (pre-conversion)
    PIPELINE_STATUSES = {STATUS_LEAD, STATUS_PROSPECT}
    # Statuses visible in the "Clients" view (converted)
    CLIENT_STATUSES = {STATUS_CLIENT, STATUS_FORMER_CLIENT}
    # Terminal statuses — no further pipeline activity
    TERMINAL_STATUSES = {STATUS_LOST, STATUS_DECEASED, STATUS_FORMER_CLIENT}

    # --- Kanban pipeline stages (FM-18 / docs/05 §5.6) ---
    STAGE_NEW = 'new_leads'
    STAGE_CONTACTED = 'contacted'
    STAGE_QUALIFIED = 'qualified'
    STAGE_IN_DISCUSSION = 'in_discussion'
    STAGE_PROPOSAL_SENT = 'proposal_sent'
    STAGE_CLOSED_WON = 'closed_won'
    STAGE_CLOSED_LOST = 'closed_lost'
    STAGE_CHOICES = [
        (STAGE_NEW, 'New Leads'),
        (STAGE_CONTACTED, 'Contacted'),
        (STAGE_QUALIFIED, 'Qualified'),
        (STAGE_IN_DISCUSSION, 'In Discussion'),
        (STAGE_PROPOSAL_SENT, 'Proposal Sent'),
        (STAGE_CLOSED_WON, 'Closed Won'),
        (STAGE_CLOSED_LOST, 'Closed Lost'),
    ]

    # Stage → Status mapping (BRU-31: stage change auto-updates status)
    STAGE_TO_STATUS = {
        STAGE_NEW: STATUS_LEAD,
        STAGE_CONTACTED: STATUS_LEAD,
        STAGE_QUALIFIED: STATUS_PROSPECT,
        STAGE_IN_DISCUSSION: STATUS_PROSPECT,
        STAGE_PROPOSAL_SENT: STATUS_PROSPECT,
        STAGE_CLOSED_WON: STATUS_CLIENT,
        STAGE_CLOSED_LOST: STATUS_LOST,
    }

    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default=SOURCE_MANUAL)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_LEAD)
    pipeline_stage = models.CharField(
        max_length=30, choices=STAGE_CHOICES, default=STAGE_NEW
    )
    assigned_advisors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name='assigned_leads',
        limit_choices_to={'role__in': ['team_lead', 'advisor']},
    )
    territory = models.ForeignKey(
        'territories.Territory',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads',
    )
    household = models.ForeignKey(
        'Household',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='members',
    )
    preferred_timezone = models.CharField(
        max_length=100, blank=True, default='',
        help_text='Lead preferred IANA timezone (e.g. America/Chicago). Falls back to tenant TZ.',
    )
    opted_out = models.BooleanField(default=False)      # BRU-07
    is_suppressed = models.BooleanField(default=False)  # BRU-19
    portal_enabled = models.BooleanField(default=False)  # True when portal account created

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'email'], name='unique_lead_email_per_tenant'
            )
        ]
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'pipeline_stage']),
            models.Index(fields=['tenant', 'email']),
            models.Index(fields=['tenant', 'territory']),
            models.Index(fields=['tenant', 'created_at']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email}) [{self.status}]"

    @property
    def is_client(self) -> bool:
        return self.status in self.ACTIVE_CLIENT_STATUSES

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


# ---------------------------------------------------------------------------
# Household (FM-17) — grouping of linked leads/clients
# ---------------------------------------------------------------------------

class Household(TenantBaseModel):
    name = models.CharField(max_length=200)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'], name='unique_household_name_per_tenant'
            )
        ]
        ordering = ['name']

    def __str__(self):
        return self.name


class HouseholdMembership(BaseModel):
    RELATIONSHIP_PRIMARY = 'primary'
    RELATIONSHIP_SPOUSE = 'spouse'
    RELATIONSHIP_DEPENDENT = 'dependent'
    RELATIONSHIP_OTHER = 'other'
    RELATIONSHIP_CHOICES = [
        (RELATIONSHIP_PRIMARY, 'Primary'),
        (RELATIONSHIP_SPOUSE, 'Spouse'),
        (RELATIONSHIP_DEPENDENT, 'Dependent'),
        (RELATIONSHIP_OTHER, 'Other'),
    ]

    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name='memberships'
    )
    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE, related_name='household_memberships'
    )
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)

    class Meta:
        unique_together = [('household', 'lead')]

    def __str__(self):
        return f"{self.lead} — {self.household} ({self.relationship})"


# ---------------------------------------------------------------------------
# ConsentRecord (FM-24 / BRU-07 / BRU-15)
# ---------------------------------------------------------------------------

class ConsentRecord(TenantBaseModel):
    CHANNEL_EMAIL = 'email'
    CHANNEL_SMS = 'sms'
    CHANNEL_CALL = 'call'
    CHANNEL_PORTAL = 'portal'
    CHANNEL_CHOICES = [
        (CHANNEL_EMAIL, 'Email'),
        (CHANNEL_SMS, 'SMS'),
        (CHANNEL_CALL, 'Call'),
        (CHANNEL_PORTAL, 'Portal'),
    ]

    STATE_GRANTED = 'granted'
    STATE_REVOKED = 'revoked'
    STATE_PENDING = 'pending'
    STATE_CHOICES = [
        (STATE_GRANTED, 'Granted'),
        (STATE_REVOKED, 'Revoked'),
        (STATE_PENDING, 'Pending'),
    ]

    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE,
        related_name='consent_records',
    )
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    purpose = models.CharField(max_length=200)
    state = models.CharField(max_length=20, choices=STATE_CHOICES)
    source = models.CharField(max_length=200)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['tenant', 'channel', 'state']),
            models.Index(fields=['tenant', 'lead', 'channel']),
        ]

    def __str__(self):
        return f"{self.channel} consent ({self.state}) — {self.lead}"


# ---------------------------------------------------------------------------
# KanbanCard (FM-18)
# ---------------------------------------------------------------------------

class KanbanCard(BaseModel):
    """
    One card per lead on the pipeline board.
    Moved via KanbanService which atomically updates lead.status + timeline + audit (BRU-31).
    Only relevant while lead.status is in PIPELINE_STATUSES.
    """
    lead = models.OneToOneField(Lead, on_delete=models.CASCADE, related_name='kanban_card')
    stage = models.CharField(max_length=30, choices=Lead.STAGE_CHOICES, default=Lead.STAGE_NEW)
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['stage', 'position']
        indexes = [
            models.Index(fields=['stage', 'position']),
        ]

    def __str__(self):
        return f"{self.lead} — {self.stage} (pos {self.position})"


# ---------------------------------------------------------------------------
# ActivityNote (FM-10 / BRU-08 / BRU-12)
# ---------------------------------------------------------------------------

class ActivityNote(TenantBaseModel):
    """
    Private and client-visible notes on the activity timeline.
    BRU-08: is_private=True notes are NEVER returned to Customer Portal consumers.
    BRU-12: all notes are recorded on the timeline.
    Linked directly to Lead — no Client FK needed (Lead IS the person).
    """

    TYPE_NOTE = 'note'
    TYPE_CALL_LOG = 'call_log'
    TYPE_EMAIL_LOG = 'email_log'
    TYPE_SMS_LOG = 'sms_log'
    TYPE_MEETING_LOG = 'meeting_log'
    TYPE_STAGE_CHANGE = 'stage_change'
    TYPE_SYSTEM = 'system'
    TYPE_CHOICES = [
        (TYPE_NOTE, 'Note'),
        (TYPE_CALL_LOG, 'Call Log'),
        (TYPE_EMAIL_LOG, 'Email Log'),
        (TYPE_SMS_LOG, 'SMS Log'),
        (TYPE_MEETING_LOG, 'Meeting Log'),
        (TYPE_STAGE_CHANGE, 'Stage Change'),
        (TYPE_SYSTEM, 'System'),
    ]

    lead = models.ForeignKey(
        Lead, on_delete=models.CASCADE,
        related_name='activity_notes',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='authored_notes',
    )
    activity_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_NOTE)
    body = models.TextField()
    is_private = models.BooleanField(default=True)  # BRU-08: default private

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'lead', 'is_private']),
            models.Index(fields=['tenant', 'created_at']),
        ]

    def __str__(self):
        visibility = 'private' if self.is_private else 'visible'
        return f"[{self.activity_type}] {visibility} note on {self.lead}"
