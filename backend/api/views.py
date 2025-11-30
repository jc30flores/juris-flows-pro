from django.db import models
from rest_framework import permissions, viewsets

from .models import (
    Activity,
    Client,
    Expense,
    GeoDepartment,
    GeoMunicipality,
    Invoice,
    InvoiceItem,
    Service,
    ServiceCategory,
    StaffUser,
)
from .serializers import (
    ActivitySerializer,
    ClientSerializer,
    ExpenseSerializer,
    GeoDepartmentSerializer,
    GeoMunicipalitySerializer,
    InvoiceItemSerializer,
    InvoiceSerializer,
    ServiceCategorySerializer,
    ServiceSerializer,
    StaffUserSerializer,
)


class ServiceCategoryViewSet(viewsets.ModelViewSet):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.AllowAny]


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.select_related("category").all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.AllowAny]


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("client").prefetch_related("items").all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.AllowAny]


class InvoiceItemViewSet(viewsets.ModelViewSet):
    queryset = InvoiceItem.objects.select_related("invoice", "service").all()
    serializer_class = InvoiceItemSerializer
    permission_classes = [permissions.AllowAny]


class ExpenseViewSet(viewsets.ModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.AllowAny]


class StaffUserViewSet(viewsets.ModelViewSet):
    queryset = StaffUser.objects.all()
    serializer_class = StaffUserSerializer
    permission_classes = [permissions.AllowAny]


class GeoDepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GeoDepartment.objects.all().order_by("name")
    serializer_class = GeoDepartmentSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None


class GeoMunicipalityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = GeoMunicipality.objects.all().order_by("name")
    serializer_class = GeoMunicipalitySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        dept_code = self.request.query_params.get("dept_code")
        if dept_code:
            qs = qs.filter(dept_code=dept_code)
        return qs


class ActivityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Activity.objects.all().order_by("description")
    serializer_class = ActivitySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = super().get_queryset()
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(description__icontains=search)
        return qs
