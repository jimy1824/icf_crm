from django.contrib import admin
from .models import FinancialProfile, FinancialAccount, FinancialGoal


@admin.register(FinancialProfile)
class FinancialProfileAdmin(admin.ModelAdmin):
    list_display = ('lead', 'tenant', 'risk_tolerance', 'updated_at')
    readonly_fields = ('id', 'updated_at', 'net_worth')
    raw_id_fields = ('lead', 'tenant')

    def net_worth(self, obj):
        return obj.net_worth
    net_worth.short_description = 'Net Worth (derived)'


@admin.register(FinancialAccount)
class FinancialAccountAdmin(admin.ModelAdmin):
    list_display = ('account_type', 'institution', 'value', 'currency', 'as_of_date', 'tenant')
    list_filter = ('account_type',)
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(FinancialGoal)
class FinancialGoalAdmin(admin.ModelAdmin):
    list_display = ('goal_type', 'lead', 'target_amount', 'target_currency', 'target_date', 'is_off_track')
    list_filter = ('goal_type', 'is_off_track')
    readonly_fields = ('id', 'created_at', 'updated_at')
