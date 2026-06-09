from django.db import transaction
from django.core.exceptions import ValidationError

from apps.employees.models import Employee, Role, EmployeeRole
from apps.users.models import CustomUser
from apps.audit.services import AuditService


class EmployeeService:

    @staticmethod
    @transaction.atomic
    def create_employee(
        *,
        tenant,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        role_slug: str,
        job_title: str = '',
        actor=None,
    ) -> Employee:
        """
        Create a CustomUser (tenant_employee) + Employee profile + initial role.
        BRU-01: employee is always scoped to tenant.
        """
        if role_slug not in Role.CORE_SLUGS:
            raise ValidationError(f"Invalid role slug: {role_slug}")

        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            user_type=CustomUser.TYPE_TENANT_EMPLOYEE,
            role=role_slug,
            tenant=tenant,
        )

        employee = Employee.objects.create(
            tenant=tenant,
            user=user,
            job_title=job_title,
        )

        role, _ = Role.objects.get_or_create(
            tenant=tenant,
            slug=role_slug,
            defaults={'name': role_slug.replace('_', ' ').title()},
        )
        EmployeeRole.objects.create(employee=employee, role=role, assigned_by=actor)

        AuditService.log(
            actor=actor,
            tenant=tenant,
            action='employee.create',
            entity_type='Employee',
            entity_id=employee.pk,
            after_state={'email': email, 'role': role_slug},
        )
        return employee

    @staticmethod
    @transaction.atomic
    def assign_role(*, employee: Employee, role_slug: str, actor=None) -> EmployeeRole:
        """Add an additional role to an employee."""
        if role_slug not in Role.CORE_SLUGS:
            raise ValidationError(f"Invalid role slug: {role_slug}")
        role, _ = Role.objects.get_or_create(
            tenant=employee.tenant,
            slug=role_slug,
            defaults={'name': role_slug.replace('_', ' ').title()},
        )
        er, created = EmployeeRole.objects.get_or_create(
            employee=employee, role=role,
            defaults={'assigned_by': actor},
        )
        if created:
            AuditService.log(
                actor=actor,
                tenant=employee.tenant,
                action='employee.role_assigned',
                entity_type='Employee',
                entity_id=employee.pk,
                after_state={'role': role_slug},
            )
        return er

    @staticmethod
    @transaction.atomic
    def deactivate_employee(*, employee: Employee, actor=None):
        """Deactivate an employee without deleting the record."""
        before = {'is_active': employee.is_active}
        employee.is_active = False
        employee.user.is_active = False
        employee.save(update_fields=['is_active', 'updated_at'])
        employee.user.save(update_fields=['is_active'])
        AuditService.log(
            actor=actor,
            tenant=employee.tenant,
            action='employee.deactivate',
            entity_type='Employee',
            entity_id=employee.pk,
            before_state=before,
            after_state={'is_active': False},
        )
