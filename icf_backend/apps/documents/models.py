from django.conf import settings
from django.db import models
from apps.common.models import TenantBaseModel


class Document(TenantBaseModel):
    TYPE_IDENTITY = 'identity'
    TYPE_FINANCIAL = 'financial'
    TYPE_TAX = 'tax'
    TYPE_CALL_RECORDING = 'call_recording'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_IDENTITY, 'Identity'),
        (TYPE_FINANCIAL, 'Financial'),
        (TYPE_TAX, 'Tax'),
        (TYPE_CALL_RECORDING, 'Call Recording'),
        (TYPE_OTHER, 'Other'),
    ]

    KYC_PENDING = 'pending'
    KYC_VERIFIED = 'verified'
    KYC_REJECTED = 'rejected'
    KYC_CHOICES = [
        (KYC_PENDING, 'Pending'),
        (KYC_VERIFIED, 'Verified'),
        (KYC_REJECTED, 'Rejected'),
    ]

    lead = models.ForeignKey(
        'leads.Lead', on_delete=models.CASCADE, related_name='documents'
    )
    doc_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    kyc_status = models.CharField(max_length=20, choices=KYC_CHOICES, default=KYC_PENDING)
    storage_ref = models.CharField(max_length=500)
    version = models.PositiveIntegerField(default=1)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True,
        related_name='uploaded_documents',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='verified_documents',
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    is_under_legal_hold = models.BooleanField(default=False)     # BRU-38
    consent_captured = models.BooleanField(default=False)        # BRU-32 for call recordings
    retain_until = models.DateField(null=True, blank=True)       # BRU-37

    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['tenant', 'lead', 'kyc_status']),
        ]

    def __str__(self):
        return f"{self.get_doc_type_display()} — {self.lead} (v{self.version})"
