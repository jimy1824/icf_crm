import pytest
from apps.notifications.models import Notification
from apps.tenants.models import Tenant
from apps.users.models import CustomUser as User


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm')


@pytest.fixture
def advisor(tenant):
    return User.objects.create_user(
        email='adv@firm.com', password='x', tenant=tenant,
        first_name='Mark', last_name='Lee', role=User.ROLE_ADVISOR,
    )


@pytest.mark.django_db
class TestNotification:
    def test_create(self, tenant, advisor):
        notif = Notification.objects.create(
            tenant=tenant,
            recipient=advisor,
            event_type='goal.off_track',
            entity_type='FinancialGoal',
            entity_id='00000000-0000-0000-0000-000000000001',
            channels=['in_app', 'email'],
        )
        assert notif.is_read is False
        assert 'in_app' in notif.channels

    def test_mark_read(self, tenant, advisor):
        notif = Notification.objects.create(
            tenant=tenant, recipient=advisor,
            event_type='lead.assigned', entity_type='Lead',
            entity_id='00000000-0000-0000-0000-000000000002',
        )
        notif.is_read = True
        notif.save()
        assert Notification.objects.get(pk=notif.pk).is_read is True
