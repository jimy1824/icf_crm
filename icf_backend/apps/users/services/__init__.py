from django.db import transaction
from apps.users.models import CustomUser


@transaction.atomic
def create_tenant_user(*, tenant, email, password, first_name, last_name, role):
    user = CustomUser.objects.create_user(
        email=email,
        password=password,
        tenant=tenant,
        first_name=first_name,
        last_name=last_name,
        role=role,
    )
    return user


def deactivate_user(*, user):
    user.is_active = False
    user.save(update_fields=['is_active'])
    return user
