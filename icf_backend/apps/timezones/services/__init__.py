"""
Timezone services — office-hour enforcement for campaign execution scheduling.
BRU-09: no automated sends outside office hours.
Uses stdlib zoneinfo (Python 3.9+) — no pytz dependency.
"""
import logging
import zoneinfo
from datetime import datetime, timedelta, time, timezone as dt_timezone

from django.utils import timezone as dj_tz

logger = logging.getLogger(__name__)

UTC = dt_timezone.utc


class TimezoneService:

    @staticmethod
    def get_tenant_config(tenant):
        """Return TenantTimeZone for tenant, creating defaults if absent."""
        from apps.timezones.models import TenantTimeZone
        config, _ = TenantTimeZone.objects.get_or_create(
            tenant=tenant,
            defaults={
                'timezone': 'America/New_York',
                'office_start': time(9, 0),
                'office_end': time(17, 0),
                'working_days': [0, 1, 2, 3, 4],
            },
        )
        return config

    @staticmethod
    def get_advisor_timezone(advisor) -> str:
        """
        Return advisor's effective timezone string.
        Priority: AdvisorTimeZone override → TenantTimeZone → UTC.
        Always queries fresh from DB to avoid stale cache.
        """
        from apps.timezones.models import AdvisorTimeZone
        override = AdvisorTimeZone.objects.filter(advisor=advisor).first()
        if override:
            return override.timezone
        try:
            config = TimezoneService.get_tenant_config(advisor.tenant)
            return config.timezone
        except Exception:
            pass
        return 'UTC'

    @staticmethod
    def shift_to_office_hours(dt: datetime, tenant) -> datetime:
        """
        Given a UTC-aware datetime, if it falls outside tenant office hours or on a
        non-working day, advance it to the start of the next valid office window.

        BRU-09: all automated outbound must land inside office hours.
        Always returns a UTC-aware datetime.
        """
        config = TimezoneService.get_tenant_config(tenant)
        tz = zoneinfo.ZoneInfo(config.timezone)
        working_days = config.get_working_days()
        office_start = config.office_start  # time object
        office_end = config.office_end      # time object

        # Convert to tenant local time
        local_dt = dt.astimezone(tz)

        max_iterations = 14  # never loop more than 2 weeks
        for _ in range(max_iterations):
            weekday = local_dt.weekday()  # 0=Mon

            if weekday not in working_days:
                local_dt = _next_working_day_start(local_dt, working_days, office_start, tz)
                continue

            local_time = local_dt.time().replace(tzinfo=None)

            if local_time < office_start:
                local_dt = local_dt.replace(
                    hour=office_start.hour, minute=office_start.minute,
                    second=0, microsecond=0,
                )
                break

            if local_time >= office_end:
                local_dt = _next_working_day_start(local_dt, working_days, office_start, tz)
                continue

            break

        return local_dt.astimezone(dt_timezone.utc)

    @staticmethod
    def set_advisor_timezone(*, advisor, timezone_str: str):
        """Create or update an advisor's personal timezone override."""
        from apps.timezones.models import AdvisorTimeZone
        obj, _ = AdvisorTimeZone.objects.update_or_create(
            advisor=advisor,
            defaults={'timezone': timezone_str},
        )
        return obj

    @staticmethod
    def update_tenant_config(*, tenant, actor, **kwargs):
        """Update tenant timezone config fields."""
        from apps.audit.services import AuditService
        config = TimezoneService.get_tenant_config(tenant)
        before = {
            'timezone': config.timezone,
            'office_start': str(config.office_start),
            'office_end': str(config.office_end),
            'working_days': config.working_days,
        }
        allowed = ('timezone', 'office_start', 'office_end', 'working_days')
        for field in allowed:
            if field in kwargs:
                setattr(config, field, kwargs[field])
        config.save()
        AuditService.log(
            tenant=tenant, actor=actor,
            action='tenant_timezone.updated',
            entity_type='TenantTimeZone', entity_id=config.pk,
            before_state=before,
            after_state={
                'timezone': config.timezone,
                'office_start': str(config.office_start),
                'office_end': str(config.office_end),
                'working_days': config.working_days,
            },
        )
        return config


def _next_working_day_start(
    local_dt: datetime,
    working_days: list,
    office_start: time,
    tz,
) -> datetime:
    """Advance local_dt to the start of the next working day at office_start."""
    candidate = (local_dt + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0,
    )
    for _ in range(7):
        if candidate.weekday() in working_days:
            return candidate.replace(
                hour=office_start.hour,
                minute=office_start.minute,
                second=0,
                microsecond=0,
            )
        candidate += timedelta(days=1)
    return (local_dt + timedelta(days=1)).replace(
        hour=office_start.hour, minute=office_start.minute, second=0, microsecond=0,
    )
