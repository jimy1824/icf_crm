import pytest
from apps.communications.models import Communication, Meeting
from apps.tenants.models import Tenant
from apps.leads.models import Lead


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Test Firm')


@pytest.fixture
def lead(tenant):
    return Lead.objects.create(
        tenant=tenant, first_name='Tom', last_name='Ford',
        email='tom@example.com', source=Lead.SOURCE_MANUAL,
    )


@pytest.mark.django_db
class TestCommunication:
    def test_create(self, tenant, lead):
        comm = Communication.objects.create(
            tenant=tenant,
            lead=lead,
            channel=Communication.CHANNEL_EMAIL,
            direction=Communication.DIRECTION_OUTBOUND,
            body_ref='s3://bucket/key',
            external_id='ext-001',
        )
        assert comm.status == Communication.STATUS_QUEUED
        assert comm.pk is not None

    def test_external_id_is_unique(self, tenant, lead):
        Communication.objects.create(
            tenant=tenant, lead=lead,
            channel=Communication.CHANNEL_EMAIL,
            direction=Communication.DIRECTION_OUTBOUND,
            body_ref='s3://bucket/key1', external_id='dup-ext',
        )
        with pytest.raises(Exception):
            Communication.objects.create(
                tenant=tenant, lead=lead,
                channel=Communication.CHANNEL_SMS,
                direction=Communication.DIRECTION_OUTBOUND,
                body_ref='s3://bucket/key2', external_id='dup-ext',
            )
