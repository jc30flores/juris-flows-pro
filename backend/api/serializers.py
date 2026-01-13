import logging
from decimal import Decimal
import logging

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from .dte_cf_service import transmit_invoice_dte
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

logger = logging.getLogger(__name__)
PRICE_OVERRIDE_ACCESS_CODE = getattr(settings, "PRICE_OVERRIDE_ACCESS_CODE", "123")


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

    def validate(self, attrs):
        nit = attrs.get("nit") or ""
        nrc = attrs.get("nrc") or ""

        nit_digits = "".join(ch for ch in nit if ch.isdigit())
        nrc_digits = "".join(ch for ch in nrc if ch.isdigit())

        if nit_digits:
            if len(nit_digits) != 14:
                raise serializers.ValidationError(
                    {"nit": "El NIT debe tener 14 dígitos"}
                )
            attrs["nit"] = nit_digits

        if nrc_digits:
            if len(nrc_digits) < 6 or len(nrc_digits) > 8:
                raise serializers.ValidationError(
                    {"nrc": "El NRC debe tener entre 6 y 8 dígitos"}
                )
            attrs["nrc"] = nrc_digits

        return attrs


class InvoiceItemSerializer(serializers.ModelSerializer):
    service_id = serializers.IntegerField(write_only=True, required=False)
    service = ServiceSerializer(read_only=True)

    class Meta:
        model = InvoiceItem
        fields = "__all__"
        extra_kwargs = {"invoice": {"required": False}}


class InvoiceServiceInputSerializer(serializers.Serializer):
    service_id = serializers.IntegerField(required=False)
    serviceId = serializers.IntegerField(required=False)
    service = serializers.IntegerField(required=False)
    name = serializers.CharField(required=False, allow_blank=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    quantity = serializers.IntegerField(min_value=1)
    subtotal = serializers.DecimalField(max_digits=12, decimal_places=2)


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, required=False)
    services = InvoiceServiceInputSerializer(many=True, write_only=True, required=False)
    date_display = serializers.SerializerMethodField()
    issue_date = serializers.DateField(source="date", read_only=True, format="%Y-%m-%d")
    numero_control = serializers.SerializerMethodField()
    codigo_generacion = serializers.SerializerMethodField()

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

        validated_data.setdefault("has_credit_note", False)

        if not validated_data.get("number"):
            validated_data["number"] = self._generate_number()

        invoice = super().create(validated_data)

        normalized_items = (
            self._normalize_services(services_data)
            if services_data is not None
            else items_data or []
        )

        self._upsert_items(invoice, normalized_items, replace=True)
        try:
            transmit_invoice_dte(
                invoice,
                force_now_timestamp=False,
                allow_generate_identifiers=True,
                source="normal_send",
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Error sending DTE for invoice %s", invoice.id, exc_info=exc
            )
        return invoice

    def get_date_display(self, obj):
        invoice_date = getattr(obj, "date", None)
        if not invoice_date:
            return None
        return invoice_date.strftime("%d/%m/%Y")

    def _extract_ident(self, payload):
        if not isinstance(payload, dict):
            return {}
        if "identificacion" in payload:
            return payload.get("identificacion") or {}
        dte_payload = payload.get("dte")
        if isinstance(dte_payload, dict) and "identificacion" in dte_payload:
            return dte_payload.get("identificacion") or {}
        documento = payload.get("documento")
        if isinstance(documento, dict) and "identificacion" in documento:
            return documento.get("identificacion") or {}
        return {}

    def _get_latest_ident(self, obj):
        record = obj.dte_records.order_by("-created_at").first()
        if not record:
            return {}
        payload = record.response_payload or record.request_payload or {}
        ident = self._extract_ident(payload)
        if not ident:
            return {}
        return ident

    def _get_latest_record(self, obj):
        return obj.dte_records.order_by("-created_at").first()

    def get_numero_control(self, obj):
        if getattr(obj, "numero_control", None):
            return obj.numero_control
        record = self._get_latest_record(obj)
        if record:
            if record.control_number:
                return record.control_number
            ident = self._extract_ident(record.request_payload or {})
            return ident.get("numeroControl") or ident.get("numero_control")
        return None

    def get_codigo_generacion(self, obj):
        if getattr(obj, "codigo_generacion", None):
            return obj.codigo_generacion
        record = self._get_latest_record(obj)
        if record:
            if record.hacienda_uuid:
                return record.hacienda_uuid
            ident = self._extract_ident(record.request_payload or {})
            return ident.get("codigoGeneracion") or ident.get("codigo_generacion")
        return None

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
            service_id = (
                service_data.get("service_id")
                or service_data.get("serviceId")
                or service_data.get("service")
            )
            if not service_id:
                continue
            quantity = service_data.get("quantity", 1)
            unit_price = service_data.get("price") or service_data.get("unit_price")
            subtotal = service_data.get("subtotal")
            override_code = service_data.get("override_code") or service_data.get(
                "overrideCode"
            )

            service_instance = Service.objects.filter(pk=service_id).first()
            original_unit_price = service_instance.base_price if service_instance else None

            if unit_price is None:
                unit_price = original_unit_price

            if unit_price is None:
                raise serializers.ValidationError(
                    {"services": f"Servicio {service_id} no tiene precio base."}
                )

            unit_price = Decimal(str(unit_price))
            original_unit_price = (
                Decimal(str(original_unit_price)) if original_unit_price is not None else unit_price
            )

            if unit_price <= 0:
                raise serializers.ValidationError(
                    {"services": f"El precio debe ser mayor a 0 para servicio {service_id}."}
                )

            price_overridden = unit_price != original_unit_price
            if price_overridden:
                if not override_code or override_code != PRICE_OVERRIDE_ACCESS_CODE:
                    raise PermissionDenied(
                        "Código de acceso inválido para modificar el precio "
                        f"del servicio {service_id}."
                    )

            if subtotal is None:
                subtotal = Decimal(unit_price) * int(quantity)

            normalized_items.append(
                {
                    "service_id": service_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "original_unit_price": original_unit_price,
                    "subtotal": subtotal,
                    "price_overridden": price_overridden,
                }
            )

        return normalized_items

    def _upsert_items(self, invoice, items_data, replace: bool = False):
        if replace:
            invoice.items.all().delete()

        for item_data in items_data:
            service_value = item_data.pop("service_id", None) or item_data.pop(
                "service",
                None,
            )

            if service_value is None:
                continue

            if isinstance(service_value, Service):
                item_data["service"] = service_value
            elif service_value is not None:
                item_data["service_id"] = service_value

            if "original_unit_price" not in item_data and "unit_price" in item_data:
                item_data["original_unit_price"] = item_data["unit_price"]
            item_data.setdefault("price_overridden", False)
            item_data.setdefault("override_reason", "")
            item_data.setdefault("override_authorized_by", "")
            item_data.setdefault("override_requested_by", "")
            item_data.setdefault("override_code_used", "")
            item_data.setdefault("override_active", False)
            item_data.setdefault("override_expires_at", None)

            InvoiceItem.objects.create(invoice=invoice, **item_data)


class ExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Expense
        fields = "__all__"


class StaffUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = StaffUser
        fields = ["id", "full_name", "username", "password", "role", "is_active"]

    def create(self, validated_data):
        pwd = validated_data.pop("password", None)
        if pwd:
            validated_data["password"] = make_password(pwd)
        return super().create(validated_data)

    def update(self, instance, validated_data):
        pwd = validated_data.pop("password", None)
        if pwd:
            instance.password = make_password(pwd)
        return super().update(instance, validated_data)


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
