import zoneinfo
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.models import BaseModel, TenantBaseModel


def validate_timezone(value: str) -> None:
    if value not in zoneinfo.available_timezones():
        raise ValidationError(f"'{value}' is not a valid IANA timezone.")


class TenantTimeZone(TenantBaseModel):
    """
    Tenant-level timezone configuration + office hours (BRU-09).
    One record per tenant. Created lazily on first access.
    """

    timezone = models.CharField(
        max_length=100,
        default='America/New_York',
        validators=[validate_timezone],
        help_text='IANA timezone identifier for the firm office.',
    )
    office_start = models.TimeField(
        default='09:00',
        help_text='Office opens (in tenant timezone).',
    )
    office_end = models.TimeField(
        default='17:00',
        help_text='Office closes (in tenant timezone).',
    )
    working_days = models.JSONField(
        default=list,
        help_text='List of weekday integers (0=Mon … 6=Sun) when office is open.',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant'], name='one_timezone_config_per_tenant'
            )
        ]

    def __str__(self):
        return f"{self.tenant_id} tz={self.timezone}"

    def get_working_days(self) -> list:
        """Return working days list, defaulting to Mon–Fri if not configured."""
        return self.working_days if self.working_days else [0, 1, 2, 3, 4]

    def save(self, *args, **kwargs):
        validate_timezone(self.timezone)
        super().save(*args, **kwargs)


class AdvisorTimeZone(BaseModel):
    """
    Per-advisor personal timezone override.
    Falls back to TenantTimeZone when not set.
    """

    advisor = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='timezone_config',
    )
    timezone = models.CharField(
        max_length=100,
        validators=[validate_timezone],
        help_text='IANA timezone override for this advisor.',
    )

    def __str__(self):
        return f"{self.advisor_id} tz={self.timezone}"

    def save(self, *args, **kwargs):
        validate_timezone(self.timezone)
        super().save(*args, **kwargs)
