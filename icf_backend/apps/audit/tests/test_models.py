import pytest
from apps.audit.models import AuditEvent
from apps.tenants.models import Tenant


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm')


@pytest.mark.django_db
class TestAuditEvent:
    def test_create(self, tenant):
        event = AuditEvent.objects.create(
            tenant=tenant,
            action='lead.create',
            entity_type='Lead',
            entity_id='00000000-0000-0000-0000-000000000001',
            after_state={'first_name': 'Alice'},
        )
        assert event.pk is not None
        assert event.timestamp is not None

    def test_immutable_on_update(self, tenant):
        # BRU-33: existing AuditEvent rows cannot be modified
        event = AuditEvent.objects.create(
            tenant=tenant,
            action='lead.create',
            entity_type='Lead',
            entity_id='00000000-0000-0000-0000-000000000002',
        )
        event.action = 'tampered'
        with pytest.raises(PermissionError):
            event.save()

    def test_immutable_on_delete(self, tenant):
        # BRU-33: AuditEvent rows cannot be deleted
        event = AuditEvent.objects.create(
            tenant=tenant,
            action='lead.create',
            entity_type='Lead',
            entity_id='00000000-0000-0000-0000-000000000003',
        )
        with pytest.raises(PermissionError):
            event.delete()
