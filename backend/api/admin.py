from django.contrib import admin

from .models import Client, Expense, Invoice, InvoiceItem, Service, ServiceCategory, StaffUser

admin.site.register(ServiceCategory)
admin.site.register(Service)
admin.site.register(Client)
admin.site.register(Invoice)
admin.site.register(InvoiceItem)
admin.site.register(Expense)
admin.site.register(StaffUser)
