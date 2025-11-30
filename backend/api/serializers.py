from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

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


class ServiceCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceCategory
        fields = "__all__"


class ServiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = "__all__"


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = "__all__"


class InvoiceItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvoiceItem
        fields = "__all__"
        extra_kwargs = {"invoice": {"required": False}}


class InvoiceServiceInputSerializer(serializers.Serializer):
    serviceId = serializers.IntegerField()
    name = serializers.CharField(required=False, allow_blank=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantity = serializers.IntegerField(min_value=1)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, required=False)
    services = InvoiceServiceInputSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Invoice
        fields = "__all__"
        extra_kwargs = {
            "number": {"required": False},
            "dte_status": {"required": False},
        }

    def create(self, validated_data):
        items_data = validated_data.pop("items", None)
        services_data = validated_data.pop("services", None)

        if not validated_data.get("dte_status"):
            validated_data["dte_status"] = Invoice.PENDING

        if not validated_data.get("number"):
            validated_data["number"] = self._generate_number()

        invoice = super().create(validated_data)

        normalized_items = (
            self._normalize_services(services_data)
            if services_data is not None
            else items_data or []
        )

        self._upsert_items(invoice, normalized_items, replace=True)
        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        services_data = validated_data.pop("services", None)

        if not validated_data.get("dte_status"):
            validated_data["dte_status"] = instance.dte_status or Invoice.PENDING

        invoice = super().update(instance, validated_data)

        if services_data is not None:
            normalized_items = self._normalize_services(services_data)
            self._upsert_items(invoice, normalized_items, replace=True)
        elif items_data is not None:
            self._upsert_items(invoice, items_data, replace=True)

        return invoice

    def _generate_number(self) -> str:
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        return f"INV-{timestamp}-{Invoice.objects.count() + 1}"

    def _normalize_services(self, services_data):
        normalized_items = []
        for service_data in services_data or []:
            service_id = service_data.get("serviceId") or service_data.get("service")
            if not service_id:
                continue
            quantity = service_data.get("quantity", 1)
            unit_price = service_data.get("price") or service_data.get("unit_price")
            subtotal = service_data.get("subtotal")

            if unit_price is None and service_id:
                service_instance = Service.objects.filter(pk=service_id).first()
                if service_instance:
                    unit_price = service_instance.base_price

            if subtotal is None and unit_price is not None:
                subtotal = Decimal(unit_price) * int(quantity)

            normalized_items.append(
                {
                    "service": service_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                }
            )

        return normalized_items

    def _upsert_items(self, invoice, items_data, replace: bool = False):
        if replace:
            invoice.items.all().delete()

        for item_data in items_data:
            InvoiceItem.objects.create(invoice=invoice, **item_data)


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = "__all__"


class StaffUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = StaffUser
        fields = "__all__"


class GeoDepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeoDepartment
        fields = ["code", "name", "normalized", "updated_at", "version"]


class GeoMunicipalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = GeoMunicipality
        fields = [
            "id",
            "dept_code",
            "muni_code",
            "name",
            "normalized",
            "updated_at",
            "version",
        ]


class ActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Activity
        fields = ["code", "description", "normalized", "updated_at", "version"]
