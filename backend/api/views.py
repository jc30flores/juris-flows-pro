from rest_framework import permissions, viewsets

from .models import (
    Client,
    Expense,
    Invoice,
    InvoiceItem,
    Service,
    ServiceCategory,
    StaffUser,
)
from .serializers import (
    ClientSerializer,
    ExpenseSerializer,
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
