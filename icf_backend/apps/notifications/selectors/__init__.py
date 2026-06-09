from apps.notifications.models import Notification


def get_unread_for_user(*, tenant, recipient):
    # BRU-01
    return Notification.objects.filter(tenant=tenant, recipient=recipient, is_read=False)


def get_all_for_user(*, tenant, recipient):
    return Notification.objects.filter(tenant=tenant, recipient=recipient)
