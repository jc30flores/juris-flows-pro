from rest_framework.routers import DefaultRouter

from .views import (
    ClientViewSet,
    ExpenseViewSet,
    InvoiceItemViewSet,
    InvoiceViewSet,
    ServiceCategoryViewSet,
    ServiceViewSet,
    StaffUserViewSet,
)

router = DefaultRouter()
router.register(r"service-categories", ServiceCategoryViewSet)
router.register(r"services", ServiceViewSet)
router.register(r"clients", ClientViewSet)
router.register(r"invoices", InvoiceViewSet)
router.register(r"invoice-items", InvoiceItemViewSet)
router.register(r"expenses", ExpenseViewSet)
router.register(r"staff-users", StaffUserViewSet)

urlpatterns = router.urls
