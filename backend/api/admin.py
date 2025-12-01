from django.contrib import admin

from .models import (
    Client,
    DTERecord,
    Expense,
    Invoice,
    InvoiceItem,
    Service,
    ServiceCategory,
    StaffUser,
)

admin.site.register(ServiceCategory)
admin.site.register(Service)
admin.site.register(Client)
admin.site.register(Invoice)
admin.site.register(InvoiceItem)
admin.site.register(Expense)
admin.site.register(StaffUser)


@admin.register(DTERecord)
class DTERecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "invoice",
        "dte_type",
        "status",
        "control_number",
        "hacienda_state",
        "total_amount",
        "issue_date",
    )
    list_filter = ("dte_type", "status", "hacienda_state", "issue_date")
    search_fields = (
        "control_number",
        "hacienda_uuid",
        "receiver_nit",
        "receiver_name",
    )
