"""
Tests for FM-14: Notification service.
BRU-07/15: channels gated by NotificationPreference.
"""
import pytest
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.tenants.models import Tenant, NotificationPreference
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm')


@pytest.fixture
def user(db, tenant):
    return CustomUser.objects.create_user(
        email='user@firm.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Mark', last_name='Lee',
    )


@pytest.mark.django_db
class TestNotificationService:

    def test_notify_creates_in_app_by_default(self, tenant, user):
        notif = NotificationService.notify(
            tenant=tenant, recipient=user,
            event_type='goal.off_track',
            entity_type='FinancialGoal', entity_id=99,
        )
        assert notif.pk is not None
        assert 'in_app' in notif.channels

    def test_mark_read(self, tenant, user):
        notif = NotificationService.notify(
            tenant=tenant, recipient=user,
            event_type='lead.assigned',
            entity_type='Lead', entity_id=1,
        )
        assert notif.is_read is False
        NotificationService.mark_read(notification=notif)
        notif.refresh_from_db()
        assert notif.is_read is True

    def test_mark_all_read(self, tenant, user):
        for i in range(3):
            NotificationService.notify(
                tenant=tenant, recipient=user,
                event_type='test.event',
                entity_type='Lead', entity_id=i,
            )
        count = NotificationService.mark_all_read(tenant=tenant, recipient=user)
        assert count == 3
        assert Notification.objects.filter(
            tenant=tenant, recipient=user, is_read=False,
        ).count() == 0

    def test_unread_count(self, tenant, user):
        for i in range(4):
            NotificationService.notify(
                tenant=tenant, recipient=user,
                event_type='test', entity_type='X', entity_id=i,
            )
        assert NotificationService.unread_count(tenant=tenant, recipient=user) == 4

    def test_bru07_email_channel_suppressed_by_preference(self, tenant, user):
        """BRU-07/15: if user disables email, notify should not include email channel."""
        NotificationPreference.objects.create(
            user=user,
            event_type='goal.off_track',
            in_app_enabled=True,
            email_enabled=False,
            sms_enabled=False,
            push_enabled=False,
        )
        notif = NotificationService.notify(
            tenant=tenant, recipient=user,
            event_type='goal.off_track',
            entity_type='FinancialGoal', entity_id=1,
            channels=['in_app', 'email'],
        )
        assert 'email' not in notif.channels
        assert 'in_app' in notif.channels

    def test_bru07_falls_back_to_in_app_if_all_disabled(self, tenant, user):
        """BRU-07/15: at minimum in_app is always delivered."""
        NotificationPreference.objects.create(
            user=user,
            event_type='lead.assigned',
            in_app_enabled=False,
            email_enabled=False,
            sms_enabled=False,
            push_enabled=False,
        )
        notif = NotificationService.notify(
            tenant=tenant, recipient=user,
            event_type='lead.assigned',
            entity_type='Lead', entity_id=1,
        )
        assert notif.channels == ['in_app']


@pytest.mark.django_db
class TestNotificationPreferenceService:

    def test_get_or_create_creates_default(self, user):
        from apps.tenants.services import NotificationPreferenceService
        pref = NotificationPreferenceService.get_or_create_preference(
            user=user, event_type='test.event',
        )
        assert pref.pk is not None
        assert pref.in_app_enabled is True

    def test_update_preference(self, user):
        from apps.tenants.services import NotificationPreferenceService
        pref = NotificationPreferenceService.update_preference(
            user=user, event_type='test.event',
            email_enabled=False, sms_enabled=True,
        )
        assert pref.email_enabled is False
        assert pref.sms_enabled is True

    def test_enabled_channels_reflects_preferences(self, user):
        from apps.tenants.services import NotificationPreferenceService
        NotificationPreference.objects.create(
            user=user, event_type='test.event',
            in_app_enabled=True, email_enabled=True,
            sms_enabled=False, push_enabled=False,
        )
        channels = NotificationPreferenceService.enabled_channels(
            user=user, event_type='test.event',
        )
        assert 'in_app' in channels
        assert 'email' in channels
        assert 'sms' not in channels

    def test_enabled_channels_defaults_to_in_app_when_no_pref(self, user):
        from apps.tenants.services import NotificationPreferenceService
        channels = NotificationPreferenceService.enabled_channels(
            user=user, event_type='nonexistent.event',
        )
        assert channels == ['in_app']
