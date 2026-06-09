import pytest
from apps.users.models import CustomUser as User
from apps.tenants.models import Tenant


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm')


@pytest.mark.django_db
class TestUser:
    def test_create_user(self, tenant):
        user = User.objects.create_user(
            email='advisor@firm.com',
            password='testpass123',
            tenant=tenant,
            first_name='Jane',
            last_name='Doe',
            role=User.ROLE_ADVISOR,
        )
        assert user.pk is not None
        assert user.is_active is True
        assert user.check_password('testpass123')

    def test_full_name(self, tenant):
        user = User.objects.create_user(
            email='a@b.com', password='x', tenant=tenant,
            first_name='John', last_name='Smith', role=User.ROLE_ADVISOR,
        )
        assert user.get_full_name() == 'John Smith'

    def test_platform_staff_has_no_tenant(self, db):
        user = User.objects.create_user(
            email='admin@platform.com', password='x',
            first_name='Super', last_name='Admin',
            role=User.ROLE_SUPER_ADMIN,
            user_type=User.TYPE_PLATFORM_STAFF,
        )
        assert user.tenant is None
        assert user.is_platform_staff is True

    def test_email_unique_per_tenant(self, tenant):
        User.objects.create_user(
            email='dup@firm.com', password='x', tenant=tenant,
            first_name='A', last_name='B', role=User.ROLE_ADVISOR,
        )
        with pytest.raises(Exception):
            User.objects.create_user(
                email='dup@firm.com', password='x', tenant=tenant,
                first_name='C', last_name='D', role=User.ROLE_ADVISOR,
            )

    def test_is_advisor(self, tenant):
        user = User(role=User.ROLE_TEAM_LEAD)
        assert user.is_advisor is True
        user.role = User.ROLE_TENANT_ADMIN
        assert user.is_advisor is False
