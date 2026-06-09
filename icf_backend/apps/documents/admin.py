from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('doc_type', 'kyc_status', 'lead', 'tenant', 'version', 'uploaded_at', 'is_under_legal_hold')
    list_filter = ('doc_type', 'kyc_status', 'is_under_legal_hold')
    readonly_fields = ('id', 'uploaded_at', 'verified_at')
    raw_id_fields = ('tenant', 'lead', 'uploaded_by', 'verified_by')
