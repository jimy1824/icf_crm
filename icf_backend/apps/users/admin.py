from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, CustomerAccount


@admin.register(CustomUser)
class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'get_full_name', 'role', 'tenant', 'is_active', 'mfa_enabled')
    list_filter = ('role', 'is_active', 'mfa_enabled')
    search_fields = ('email', 'first_name', 'last_name')
    readonly_fields = ('id', 'date_joined')
    ordering = ('email',)
    fieldsets = (
        (None, {'fields': ('id', 'email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Organisation', {'fields': ('tenant', 'role')}),
        ('Security', {'fields': ('mfa_enabled', 'is_active', 'is_staff', 'is_superuser')}),
        ('Dates', {'fields': ('date_joined', 'last_login')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'tenant'),
        }),
    )


@admin.register(CustomerAccount)
class CustomerAccountAdmin(BaseUserAdmin):
    list_display = ('email', 'lead', 'tenant', 'is_active', 'date_joined', 'last_login')
    list_filter = ('is_active', 'tenant')
    search_fields = ('email', 'lead__first_name', 'lead__last_name')
    readonly_fields = ('id', 'date_joined', 'last_login')
    ordering = ('email',)
    # BaseUserAdmin expects these; clear the ones that reference CustomUser-only fields
    filter_horizontal = ()
    fieldsets = (
        (None, {'fields': ('id', 'email', 'password')}),
        ('Linked records', {'fields': ('lead', 'tenant')}),
        ('Status', {'fields': ('is_active', 'date_joined', 'last_login')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'lead', 'tenant'),
        }),
    )
