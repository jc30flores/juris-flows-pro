from rest_framework import serializers

from .models import (
    Client,
    Expense,
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


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, required=False)

    class Meta:
        model = Invoice
        fields = "__all__"

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        invoice = super().create(validated_data)
        self._upsert_items(invoice, items_data, replace=True)
        return invoice

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        invoice = super().update(instance, validated_data)

        if items_data is not None:
            self._upsert_items(invoice, items_data, replace=True)

        return invoice

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
