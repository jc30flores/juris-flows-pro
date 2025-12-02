from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ActivityViewSet,
    ConnectivityStatusView,
    ClientViewSet,
    ExpenseViewSet,
    GeoDepartmentViewSet,
    GeoMunicipalityViewSet,
    InvoiceItemViewSet,
    InvoiceViewSet,
    LoginView,
    LogoutView,
    ServiceCategoryViewSet,
    ServiceViewSet,
    StaffUserViewSet,
)

router = DefaultRouter()
router.register(r"service-categories", ServiceCategoryViewSet)
router.register(r"services", ServiceViewSet)
router.register(r"clients", ClientViewSet)
router.register(r"invoices", InvoiceViewSet, basename="invoice")
router.register(r"invoice-items", InvoiceItemViewSet)
router.register(r"expenses", ExpenseViewSet)
router.register(r"staff-users", StaffUserViewSet)
router.register(r"geo/departments", GeoDepartmentViewSet)
router.register(r"geo/municipalities", GeoMunicipalityViewSet)
router.register(r"activities", ActivityViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("status/connectivity/", ConnectivityStatusView.as_view(), name="connectivity-status"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
]
