from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('user_type', CustomUser.TYPE_PLATFORM_STAFF)
        extra_fields.setdefault('role', CustomUser.ROLE_SUPER_ADMIN)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    # --- User types: determines which platform this user may log in to ---
    TYPE_PLATFORM_STAFF = 'platform_staff'   # Super Panel only
    TYPE_TENANT_EMPLOYEE = 'tenant_employee'  # Tenant CRM only
    TYPE_CUSTOMER = 'customer'               # Customer Portal only (leads/clients)
    TYPE_CHOICES = [
        (TYPE_PLATFORM_STAFF, 'Platform Staff'),
        (TYPE_TENANT_EMPLOYEE, 'Tenant Employee'),
        (TYPE_CUSTOMER, 'Customer'),
    ]

    # --- Roles ---
    ROLE_SUPER_ADMIN = 'super_admin'
    ROLE_SUPPORT = 'support'
    ROLE_COMPLIANCE = 'compliance_officer'
    ROLE_TENANT_ADMIN = 'tenant_admin'
    ROLE_TEAM_LEAD = 'team_lead'
    ROLE_ADVISOR = 'advisor'
    ROLE_SERVICE = 'service'
    ROLE_CHOICES = [
        (ROLE_SUPER_ADMIN, 'Super Admin'),
        (ROLE_SUPPORT, 'Support'),
        (ROLE_COMPLIANCE, 'Compliance Officer'),
        (ROLE_TENANT_ADMIN, 'Tenant Admin'),
        (ROLE_TEAM_LEAD, 'Team Lead / Senior Advisor'),
        (ROLE_ADVISOR, 'Advisor'),
        (ROLE_SERVICE, 'Service / Integration Account'),
    ]

    # --- Role groupings ---
    PLATFORM_ROLES = {ROLE_SUPER_ADMIN, ROLE_SUPPORT, ROLE_COMPLIANCE}
    EMPLOYEE_ROLES = {ROLE_TENANT_ADMIN, ROLE_TEAM_LEAD, ROLE_ADVISOR}
    ADVISOR_ROLES = {ROLE_TEAM_LEAD, ROLE_ADVISOR}

    user_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_TENANT_EMPLOYEE,
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='users',
    )
    role = models.CharField(max_length=30, choices=ROLE_CHOICES)
    email = models.EmailField()
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    mfa_enabled = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'role', 'user_type']

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'email'],
                condition=models.Q(tenant__isnull=False),
                name='unique_email_per_tenant',
            ),
        ]

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}>"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def is_platform_staff(self):
        return self.user_type == self.TYPE_PLATFORM_STAFF

    @property
    def is_tenant_employee(self):
        return self.user_type == self.TYPE_TENANT_EMPLOYEE

    @property
    def is_advisor(self):
        return self.role in self.ADVISOR_ROLES


# ---------------------------------------------------------------------------
# CustomerAccount (Customer Portal auth — separate from CustomUser)
# Customers (leads/clients) authenticate via this model, never via CustomUser.
# ---------------------------------------------------------------------------

class CustomerAccountManager(BaseUserManager):
    def create_user(self, email, lead, tenant, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        account = self.model(email=email, lead=lead, tenant=tenant, **extra_fields)
        account.set_password(password)
        account.save(using=self._db)
        return account


class CustomerAccount(AbstractBaseUser):
    """
    Portal authentication model for leads/clients (user_type='customer').
    Completely separate from CustomUser — never mixed in auth flows.
    USERNAME_FIELD = 'email' (copied/synced from lead.email on creation).
    """

    user_type = 'customer'  # constant, not a DB field

    email = models.EmailField(unique=True)
    lead = models.OneToOneField(
        'leads.Lead',
        on_delete=models.CASCADE,
        related_name='customer_account',
    )
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='customer_accounts',
    )
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)

    objects = CustomerAccountManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['lead', 'tenant']

    class Meta:
        indexes = [
            models.Index(fields=['tenant', 'email']),
            models.Index(fields=['tenant', 'is_active']),
        ]

    def __str__(self):
        return f"CustomerAccount <{self.email}> [{self.tenant_id}]"

    @property
    def is_portal_user(self):
        return True
