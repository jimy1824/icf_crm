"""
API tests for FM-04: Support ticketing endpoints.
Tests permission gates, status transitions, tenant isolation.
"""
import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.support.models import SupportTicket
from apps.tenants.models import Tenant
from apps.users.models import CustomUser


@pytest.fixture
def tenant(db):
    return Tenant.objects.create(firm_name='Alpha Firm')


@pytest.fixture
def other_tenant(db):
    return Tenant.objects.create(firm_name='Beta Firm')


@pytest.fixture
def user(db, tenant):
    return CustomUser.objects.create_user(
        email='user@alpha.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Jane', last_name='Doe',
    )


@pytest.fixture
def support_staff(db, tenant):
    return CustomUser.objects.create_user(
        email='support@platform.com', password='pass',
        tenant=tenant, role=CustomUser.ROLE_SUPPORT,
        first_name='Bob', last_name='S',
    )


@pytest.fixture
def other_user(db, other_tenant):
    return CustomUser.objects.create_user(
        email='user@beta.com', password='pass',
        tenant=other_tenant, role=CustomUser.ROLE_ADVISOR,
        first_name='Other', last_name='User',
    )


def auth_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.mark.django_db
class TestTicketListCreate:

    def test_unauthenticated_rejected(self):
        c = APIClient()
        resp = c.get('/api/v1/support/tickets/')
        assert resp.status_code == 401

    def test_list_returns_own_tickets(self, user, tenant):
        c = auth_client(user)
        # Create a ticket first
        c.post('/api/v1/support/tickets/', {
            'subject': 'My Issue', 'body': 'Details',
        }, format='json')
        resp = c.get('/api/v1/support/tickets/')
        assert resp.status_code == 200
        assert len(resp.data) >= 1

    def test_create_ticket(self, user, tenant):
        c = auth_client(user)
        resp = c.post('/api/v1/support/tickets/', {
            'subject': 'Login error', 'body': 'Cannot log in.',
            'category': 'technical', 'priority': 'high',
        }, format='json')
        assert resp.status_code == 201
        assert resp.data['status'] == SupportTicket.STATUS_OPEN

    def test_bru01_user_cannot_see_other_tenant_tickets(self, user, other_user, tenant):
        # Other tenant creates ticket
        c_other = auth_client(other_user)
        c_other.post('/api/v1/support/tickets/', {
            'subject': 'Other issue', 'body': 'Details',
        }, format='json')
        c_mine = auth_client(user)
        resp = c_mine.get('/api/v1/support/tickets/')
        assert resp.status_code == 200
        subjects = [t['subject'] for t in resp.data]
        assert 'Other issue' not in subjects


@pytest.mark.django_db
class TestTicketStatusTransition:

    def test_support_can_transition(self, user, support_staff, tenant):
        c_user = auth_client(user)
        resp = c_user.post('/api/v1/support/tickets/', {
            'subject': 'Issue', 'body': 'Body',
        }, format='json')
        ticket_id = resp.data['id']

        c_support = auth_client(support_staff)
        resp2 = c_support.post(
            f'/api/v1/support/tickets/{ticket_id}/status/',
            {'status': SupportTicket.STATUS_IN_PROGRESS}, format='json',
        )
        assert resp2.status_code == 200
        assert resp2.data['status'] == SupportTicket.STATUS_IN_PROGRESS

    def test_regular_user_cannot_transition(self, user, tenant):
        c = auth_client(user)
        resp = c.post('/api/v1/support/tickets/', {
            'subject': 'Issue', 'body': 'Body',
        }, format='json')
        ticket_id = resp.data['id']
        resp2 = c.post(
            f'/api/v1/support/tickets/{ticket_id}/status/',
            {'status': SupportTicket.STATUS_IN_PROGRESS}, format='json',
        )
        assert resp2.status_code == 403


@pytest.mark.django_db
class TestTicketComments:

    def test_add_comment(self, user, tenant):
        c = auth_client(user)
        resp = c.post('/api/v1/support/tickets/', {
            'subject': 'Help', 'body': 'Body',
        }, format='json')
        ticket_id = resp.data['id']
        resp2 = c.post(
            f'/api/v1/support/tickets/{ticket_id}/comments/',
            {'body': 'Here is more info.'}, format='json',
        )
        assert resp2.status_code == 201
        assert resp2.data['body'] == 'Here is more info.'
        assert resp2.data['is_internal'] is False

    def test_regular_user_cannot_post_internal(self, user, tenant):
        c = auth_client(user)
        resp = c.post('/api/v1/support/tickets/', {
            'subject': 'Help', 'body': 'Body',
        }, format='json')
        ticket_id = resp.data['id']
        resp2 = c.post(
            f'/api/v1/support/tickets/{ticket_id}/comments/',
            {'body': 'Internal note.', 'is_internal': True}, format='json',
        )
        # Silently demoted to public
        assert resp2.status_code == 201
        assert resp2.data['is_internal'] is False
