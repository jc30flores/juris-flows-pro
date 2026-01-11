import logging
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from .dte_cf_service import (
    send_ccf_dte_for_invoice,
    send_cf_dte_for_invoice,
    send_se_dte_for_invoice,
)
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
    is_no_sujeta = serializers.BooleanField(required=False)
    isNoSujeta = serializers.BooleanField(required=False)


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceItemSerializer(many=True, required=False)
    services = InvoiceServiceInputSerializer(many=True, write_only=True, required=False)
    override_token = serializers.CharField(write_only=True, required=False)
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
        validated_data.pop("override_token", None)
        staff_user = self.context.get("staff_user")
        request = self.context.get("request")

        normalized_items = (
            self._normalize_services(services_data, request, staff_user)
            if services_data is not None
            else items_data or []
        )

        if normalized_items:
            validated_data["total"] = self._calculate_total(normalized_items)

        if not validated_data.get("dte_status"):
            validated_data["dte_status"] = Invoice.PENDING

        validated_data.setdefault("has_credit_note", False)

        if not validated_data.get("number"):
            validated_data["number"] = self._generate_number()

        invoice = super().create(validated_data)

        self._upsert_items(invoice, normalized_items, replace=True)
        try:
            if invoice.doc_type == Invoice.CF:
                send_cf_dte_for_invoice(invoice, staff_user=staff_user)
            elif invoice.doc_type == Invoice.CCF:
                send_ccf_dte_for_invoice(invoice, staff_user=staff_user)
            elif invoice.doc_type == Invoice.SX:
                send_se_dte_for_invoice(invoice, staff_user=staff_user)
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
        record = self._get_latest_record(obj)
        if record:
            if record.control_number:
                return record.control_number
            ident = self._extract_ident(record.request_payload or {})
            return ident.get("numeroControl") or ident.get("numero_control")
        return None

    def get_codigo_generacion(self, obj):
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
        validated_data.pop("override_token", None)
        staff_user = self.context.get("staff_user")
        request = self.context.get("request")

        if not validated_data.get("dte_status"):
            validated_data["dte_status"] = instance.dte_status or Invoice.PENDING

        normalized_items = None
        if services_data is not None:
            normalized_items = self._normalize_services(
                services_data, request, staff_user
            )
            validated_data["total"] = self._calculate_total(normalized_items)
        elif items_data is not None:
            normalized_items = items_data

        invoice = super().update(instance, validated_data)

        if normalized_items is not None:
            self._upsert_items(invoice, normalized_items, replace=True)

        return invoice

    def _generate_number(self) -> str:
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        return f"INV-{timestamp}-{Invoice.objects.count() + 1}"

    def _calculate_total(self, items_data) -> Decimal:
        total = Decimal("0")
        for item in items_data or []:
            quantity = int(item.get("quantity", 1))
            unit_price = Decimal(str(item.get("unit_price")))
            subtotal = item.get("subtotal")
            if subtotal is None:
                subtotal = unit_price * quantity
            total += Decimal(str(subtotal))
        return total

    def _get_override_token(self, request):
        if not request:
            return None
        return (
            request.headers.get("X-PRICE-OVERRIDE-TOKEN")
            or request.data.get("override_token")
        )

    def _authorize_price_override(
        self, service_id, override_code, request, staff_user
    ) -> None:
        from .utils import validate_price_override_token

        override_token = self._get_override_token(request)
        if settings.DEBUG and request is not None:
            logger.info(
                "Price override check (service=%s, user=%s, auth=%s, session_key=%s, payload_keys=%s)",
                service_id,
                getattr(getattr(request, "user", None), "id", None),
                bool(getattr(request, "auth", None)),
                getattr(getattr(request, "session", None), "session_key", None),
                list(getattr(request, "data", {}).keys()),
            )
        if override_token and validate_price_override_token(override_token, staff_user):
            return

        if override_code and override_code == PRICE_OVERRIDE_ACCESS_CODE:
            return

        if settings.DEBUG:
            logger.warning(
                "Price override denied for service %s (staff_user=%s, token_present=%s)",
                service_id,
                getattr(staff_user, "id", None),
                bool(override_token),
            )
        raise PermissionDenied(
            "Price override requires authorization for "
            f"service {service_id}."
        )

    def _normalize_services(self, services_data, request, staff_user):
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
            is_no_sujeta = service_data.get("is_no_sujeta")
            if is_no_sujeta is None:
                is_no_sujeta = service_data.get("isNoSujeta", False)

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
                self._authorize_price_override(
                    service_id, override_code, request, staff_user
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
                    "is_no_sujeta": bool(is_no_sujeta),
                    "override_authorized_by": staff_user if price_overridden else None,
                    "override_authorized_at": timezone.now()
                    if price_overridden
                    else None,
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
            item_data.setdefault("is_no_sujeta", False)

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
