from django.contrib import admin
from .models import Tenant, SubscriptionPlan, TenantSubscription


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('firm_name', 'status', 'region', 'timezone', 'created_at')
    list_filter = ('status',)
    search_fields = ('firm_name',)
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'max_leads', 'max_users', 'max_storage_gb', 'is_active')
    list_filter = ('is_active',)
    readonly_fields = ('id',)


@admin.register(TenantSubscription)
class TenantSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'plan', 'status', 'starts_at', 'ends_at')
    list_filter = ('status',)
    readonly_fields = ('id', 'created_at', 'updated_at')
