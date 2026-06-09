from django.conf import settings
from django.db import models
from apps.common.models import BaseModel, TenantBaseModel


class SupportTicket(TenantBaseModel):
    """
    FM-04: support/ticketing lifecycle.
    Created by tenant users; managed by Super Admin support staff.
    """
    PRIORITY_LOW = 'low'
    PRIORITY_NORMAL = 'normal'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_NORMAL, 'Normal'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_URGENT, 'Urgent'),
    ]

    STATUS_OPEN = 'open'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_WAITING = 'waiting_on_customer'
    STATUS_RESOLVED = 'resolved'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_WAITING, 'Waiting on Customer'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_CLOSED, 'Closed'),
    ]

    CATEGORY_TECHNICAL = 'technical'
    CATEGORY_BILLING = 'billing'
    CATEGORY_ACCOUNT = 'account'
    CATEGORY_FEATURE = 'feature_request'
    CATEGORY_OTHER = 'other'
    CATEGORY_CHOICES = [
        (CATEGORY_TECHNICAL, 'Technical'),
        (CATEGORY_BILLING, 'Billing'),
        (CATEGORY_ACCOUNT, 'Account'),
        (CATEGORY_FEATURE, 'Feature Request'),
        (CATEGORY_OTHER, 'Other'),
    ]

    subject = models.CharField(max_length=300)
    body = models.TextField()
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default=CATEGORY_OTHER)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_OPEN)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='created_tickets',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_tickets',
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status']),
            models.Index(fields=['tenant', 'priority']),
            models.Index(fields=['assigned_to', 'status']),
        ]

    def __str__(self):
        return f"[{self.priority.upper()}] {self.subject} ({self.status})"


class TicketComment(BaseModel):
    """Threaded comments on a support ticket."""
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name='ticket_comments',
    )
    body = models.TextField()
    is_internal = models.BooleanField(default=False)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Comment on {self.ticket_id} by {self.author_id}"
