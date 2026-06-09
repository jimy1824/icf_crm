from rest_framework import serializers

from apps.tenants.models import (
    BillingRecord,
    SubscriptionPlan,
    Tenant,
    TenantBranding,
    TenantSubscription,
)


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'max_leads', 'max_users', 'max_storage_gb',
            'max_campaigns', 'features',
        ]


class TenantSubscriptionSerializer(serializers.ModelSerializer):
    plan = SubscriptionPlanSerializer(read_only=True)

    class Meta:
        model = TenantSubscription
        fields = [
            'id', 'plan', 'status', 'billing_cycle',
            'is_trial', 'trial_expires_at',
            'starts_at', 'ends_at',
            'payment_due_date', 'grace_period_ends_at',
        ]
        read_only_fields = fields


class TenantSerializer(serializers.ModelSerializer):
    subscription = TenantSubscriptionSerializer(read_only=True)

    class Meta:
        model = Tenant
        fields = [
            'id', 'firm_name', 'legal_name', 'registration_number', 'tax_number',
            'website', 'company_email', 'phone', 'logo_url',
            'address_line1', 'address_line2', 'city', 'state', 'country', 'postal_code',
            'status', 'region', 'timezone',
            'subdomain', 'custom_domain', 'domain_status',
            'login_disabled',
            'created_at', 'subscription',
        ]
        read_only_fields = ['id', 'created_at', 'domain_status']


class TenantCreateSerializer(serializers.Serializer):
    firm_name = serializers.CharField(max_length=200)
    legal_name = serializers.CharField(max_length=200, default='', allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True, default='')
    company_email = serializers.EmailField(required=False, allow_blank=True, default='')
    phone = serializers.CharField(max_length=30, default='', allow_blank=True)
    address_line1 = serializers.CharField(max_length=200, default='', allow_blank=True)
    city = serializers.CharField(max_length=100, default='', allow_blank=True)
    state = serializers.CharField(max_length=100, default='', allow_blank=True)
    country = serializers.CharField(max_length=100, default='US')
    postal_code = serializers.CharField(max_length=20, default='', allow_blank=True)
    region = serializers.CharField(max_length=100, default='', allow_blank=True)
    timezone = serializers.CharField(max_length=63, default='America/New_York')
    plan_id = serializers.IntegerField()
    is_trial = serializers.BooleanField(default=False)
    trial_days = serializers.IntegerField(default=14, min_value=1)


class TenantProfileUpdateSerializer(serializers.Serializer):
    firm_name = serializers.CharField(max_length=200, required=False)
    legal_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    registration_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    tax_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    company_email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    logo_url = serializers.URLField(required=False, allow_blank=True)
    address_line1 = serializers.CharField(max_length=200, required=False, allow_blank=True)
    address_line2 = serializers.CharField(max_length=200, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    subdomain = serializers.SlugField(max_length=100, required=False, allow_blank=True)
    custom_domain = serializers.CharField(max_length=255, required=False, allow_blank=True)
    region = serializers.CharField(max_length=100, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=63, required=False)


class TenantUsageSerializer(serializers.Serializer):
    leads = serializers.DictField()
    users = serializers.DictField()
    campaigns = serializers.DictField()
    plan = serializers.CharField(allow_null=True)
    subscription_status = serializers.CharField(allow_null=True)
    is_trial = serializers.BooleanField()
    trial_expires_at = serializers.CharField(allow_null=True)


class ExtendTrialSerializer(serializers.Serializer):
    days = serializers.IntegerField(min_value=1, max_value=365)


class TenantBrandingSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantBranding
        fields = [
            'id', 'primary_color', 'secondary_color', 'login_bg_url',
            'custom_smtp_host', 'custom_smtp_port', 'custom_smtp_user',
            'custom_sms_provider', 'updated_at',
        ]
        read_only_fields = ['id', 'updated_at']


class TenantBrandingUpdateSerializer(serializers.Serializer):
    primary_color = serializers.CharField(max_length=7, required=False)
    secondary_color = serializers.CharField(max_length=7, required=False)
    login_bg_url = serializers.URLField(required=False, allow_blank=True)
    custom_smtp_host = serializers.CharField(max_length=255, required=False, allow_blank=True)
    custom_smtp_port = serializers.IntegerField(min_value=1, max_value=65535, required=False)
    custom_smtp_user = serializers.CharField(max_length=255, required=False, allow_blank=True)
    custom_sms_provider = serializers.CharField(max_length=50, required=False, allow_blank=True)


class BillingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillingRecord
        fields = [
            'id', 'record_type', 'status', 'amount_cents', 'currency',
            'period_start', 'period_end', 'external_invoice_id',
            'invoice_number', 'tax_amount_cents', 'discount_amount_cents',
            'payment_method', 'transaction_id', 'paid_at', 'notes',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class BillingRecordCreateSerializer(serializers.Serializer):
    amount_cents = serializers.IntegerField(min_value=0)
    currency = serializers.CharField(max_length=3, default='USD')
    period_start = serializers.DateField()
    period_end = serializers.DateField()
    external_invoice_id = serializers.CharField(max_length=255, default='', allow_blank=True)
    invoice_number = serializers.CharField(max_length=100, default='', allow_blank=True)
    tax_amount_cents = serializers.IntegerField(min_value=0, default=0)
    discount_amount_cents = serializers.IntegerField(min_value=0, default=0)


class RecordPaymentSerializer(serializers.Serializer):
    payment_method = serializers.ChoiceField(
        choices=['card', 'bank_transfer', 'check', 'other'], required=False,
        allow_blank=True,
    )
    transaction_id = serializers.CharField(max_length=255, default='', allow_blank=True)


class SubscriptionPlanCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=100)
    max_leads = serializers.IntegerField(min_value=0)
    max_users = serializers.IntegerField(min_value=0)
    max_storage_gb = serializers.IntegerField(min_value=0)
    max_campaigns = serializers.IntegerField(min_value=0, default=0)
    features = serializers.DictField(default=dict)


# ---------------------------------------------------------------------------
# Company-facing serializers (tenant employee access to own tenant)
# ---------------------------------------------------------------------------

class CompanySettingsSerializer(serializers.ModelSerializer):
    """Read/write serializer for a tenant employee updating their own firm profile."""
    subscription = TenantSubscriptionSerializer(read_only=True)

    class Meta:
        model = Tenant
        fields = [
            'id', 'firm_name', 'legal_name', 'registration_number', 'tax_number',
            'website', 'company_email', 'phone', 'logo_url',
            'address_line1', 'address_line2', 'city', 'state', 'country', 'postal_code',
            'region', 'timezone', 'status', 'subscription', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'created_at']


class CompanySettingsUpdateSerializer(serializers.Serializer):
    firm_name = serializers.CharField(max_length=200, required=False)
    legal_name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    registration_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    tax_number = serializers.CharField(max_length=100, required=False, allow_blank=True)
    website = serializers.URLField(required=False, allow_blank=True)
    company_email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(max_length=30, required=False, allow_blank=True)
    address_line1 = serializers.CharField(max_length=200, required=False, allow_blank=True)
    address_line2 = serializers.CharField(max_length=200, required=False, allow_blank=True)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True)
    state = serializers.CharField(max_length=100, required=False, allow_blank=True)
    country = serializers.CharField(max_length=100, required=False)
    postal_code = serializers.CharField(max_length=20, required=False, allow_blank=True)
    region = serializers.CharField(max_length=100, required=False, allow_blank=True)
    timezone = serializers.CharField(max_length=63, required=False)


class LogoUrlUpdateSerializer(serializers.Serializer):
    logo_url = serializers.URLField()


from apps.tenants.models import NotificationPreference  # noqa: E402


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = ['id', 'event_type', 'email_enabled', 'sms_enabled', 'in_app_enabled', 'push_enabled']
        read_only_fields = ['id']


class NotificationPreferenceBulkUpdateSerializer(serializers.Serializer):
    preferences = serializers.ListField(
        child=serializers.DictField(),
        min_length=1,
    )

    def validate_preferences(self, value):
        allowed_channels = {'email_enabled', 'sms_enabled', 'in_app_enabled', 'push_enabled'}
        for item in value:
            if 'event_type' not in item:
                raise serializers.ValidationError("Each preference must have 'event_type'.")
            unknown = set(item.keys()) - {'event_type'} - allowed_channels
            if unknown:
                raise serializers.ValidationError(f"Unknown fields: {unknown}")
        return value
