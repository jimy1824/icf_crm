from django.contrib import admin
from .models import Campaign, CampaignStep, CampaignEnrollment


class CampaignStepInline(admin.TabularInline):
    model = CampaignStep
    extra = 0
    ordering = ['step_number']


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ('name', 'tenant', 'status', 'created_by', 'created_at')
    list_filter = ('status',)
    search_fields = ('name',)
    readonly_fields = ('id', 'created_at', 'updated_at')
    inlines = [CampaignStepInline]


@admin.register(CampaignEnrollment)
class CampaignEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('campaign', 'tenant', 'status', 'current_step', 'enrolled_at')
    list_filter = ('status', 'stopped_reason')
    readonly_fields = ('id', 'enrolled_at', 'updated_at')
