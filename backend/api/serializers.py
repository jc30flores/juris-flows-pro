import logging
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core import signing
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from .dte_cf_service import send_dte_for_invoice
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
PRICE_OVERRIDE_TOKEN_MAX_AGE = getattr(settings, "PRICE_OVERRIDE_TOKEN_MAX_AGE", 300)
PRICE_OVERRIDE_TOKEN_SALT = "price-override"


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

    def create(self, validated_data):
        if "original_unit_price" not in validated_data:
            validated_data["original_unit_price"] = validated_data.get("unit_price") or 0
        if validated_data.get("price_overridden") is None:
            validated_data["price_overridden"] = False
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if "original_unit_price" not in validated_data:
            validated_data["original_unit_price"] = (
                getattr(instance, "original_unit_price", None)
                or validated_data.get("unit_price")
                or 0
            )
        if "price_overridden" not in validated_data or validated_data.get("price_overridden") is None:
            validated_data["price_overridden"] = (
                getattr(instance, "price_overridden", False) or False
            )
        return super().update(instance, validated_data)


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
    override_token = serializers.CharField(write_only=True, required=False, allow_blank=True)
    date_display = serializers.SerializerMethodField()
    issue_date = serializers.DateField(source="date", read_only=True, format="%Y-%m-%d")
    numero_control = serializers.SerializerMethodField()
    codigo_generacion = serializers.SerializerMethodField()
    sello_recibido = serializers.SerializerMethodField()
    fec_emi = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = "__all__"
        extra_kwargs = {
            "number": {"required": False},
            "dte_status": {"required": False},
        }

    def validate_dte_status(self, value):
        if value is None:
            return value
        return str(value).upper()

    def create(self, validated_data):
        items_data = validated_data.pop("items", None)
        services_data = validated_data.pop("services", None)
        override_token = validated_data.pop("override_token", None)

        if not validated_data.get("dte_status"):
            validated_data["dte_status"] = Invoice.PENDING
        else:
            validated_data["dte_status"] = str(validated_data["dte_status"]).upper()

        validated_data.setdefault("has_credit_note", False)

        if not validated_data.get("number"):
            validated_data["number"] = self._generate_number()

        normalized_items = (
            self._normalize_services(
                services_data,
                override_token=override_token,
                request=self.context.get("request"),
            )
            if services_data is not None
            else items_data or []
        )

        if normalized_items:
            validated_data["total"] = self._calculate_total(normalized_items)

        invoice = super().create(validated_data)

        self._upsert_items(invoice, normalized_items, replace=True)
        try:
            send_dte_for_invoice(
                invoice,
                ensure_identifiers=True,
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

    def _extract_hacienda_response(self, payload):
        if not isinstance(payload, dict):
            return {}
        hresp = payload.get("respuesta_hacienda") or payload.get("hacienda_response")
        if isinstance(hresp, dict):
            return hresp
        hresp = payload.get("respuestaHacienda") or payload.get("haciendaResponse")
        if isinstance(hresp, dict):
            return hresp
        return {}

    def get_sello_recibido(self, obj):
        record = self._get_latest_record(obj)
        if not record:
            return None
        hresp = self._extract_hacienda_response(record.response_payload or {})
        return hresp.get("selloRecibido") or hresp.get("sello_recibido")

    def get_fec_emi(self, obj):
        record = self._get_latest_record(obj)
        if not record:
            return None
        ident = self._extract_ident(record.request_payload or {})
        fec_emi = ident.get("fecEmi") or ident.get("fec_emi")
        if not fec_emi and record.issue_date:
            return record.issue_date.strftime("%Y-%m-%d")
        return fec_emi

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)
        services_data = validated_data.pop("services", None)
        override_token = validated_data.pop("override_token", None)

        if not validated_data.get("dte_status"):
            validated_data["dte_status"] = instance.dte_status or Invoice.PENDING
        else:
            validated_data["dte_status"] = str(validated_data["dte_status"]).upper()

        if services_data is not None:
            normalized_items = self._normalize_services(
                services_data,
                override_token=override_token,
                request=self.context.get("request"),
            )
            validated_data["total"] = self._calculate_total(normalized_items)
        elif items_data is not None:
            validated_data["total"] = self._calculate_total(items_data)

        invoice = super().update(instance, validated_data)

        if services_data is not None:
            self._upsert_items(invoice, normalized_items, replace=True)
        elif items_data is not None:
            self._upsert_items(invoice, items_data, replace=True)

        return invoice

    def _generate_number(self) -> str:
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        return f"INV-{timestamp}-{Invoice.objects.count() + 1}"

    def _calculate_total(self, items_data):
        total = Decimal("0")
        for item in items_data or []:
            quantity = Decimal(str(item.get("quantity") or 0))
            if quantity <= 0:
                raise serializers.ValidationError(
                    {"services": "La cantidad debe ser mayor a 0."}
                )
            unit_price = item.get("unit_price") or item.get("price")
            if unit_price is None:
                unit_price = 0
            unit_price = Decimal(str(unit_price))
            subtotal = item.get("subtotal")
            subtotal_value = (
                Decimal(str(subtotal))
                if subtotal is not None
                else unit_price * quantity
            )
            if subtotal_value <= 0:
                raise serializers.ValidationError(
                    {"services": "El subtotal debe ser mayor a 0."}
                )
            total += subtotal_value
        return total

    def _normalize_services(self, services_data, *, override_token=None, request=None):
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
                self._ensure_price_override_authorized(
                    override_token=override_token,
                    request=request,
                    service_id=service_id,
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

    def _ensure_price_override_authorized(self, *, override_token, request, service_id):
        token = override_token
        if not token and request is not None:
            token = request.data.get("override_token")
        if token:
            try:
                payload = signing.loads(
                    token,
                    salt=PRICE_OVERRIDE_TOKEN_SALT,
                    max_age=PRICE_OVERRIDE_TOKEN_MAX_AGE,
                )
            except signing.BadSignature:
                payload = None
            if payload and payload.get("authorized") is True:
                return

        self._log_price_override_denied(request=request, service_id=service_id)
        raise PermissionDenied(
            "La modificación de precio requiere autorización válida."
        )

    def _log_price_override_denied(self, *, request, service_id):
        if not settings.DEBUG:
            return
        user = getattr(request, "user", None) if request else None
        logger.debug(
            "Price override denied for service %s. user=%s auth=%s session=%s data_keys=%s",
            service_id,
            getattr(user, "username", None) if user else None,
            getattr(request, "auth", None) if request else None,
            list(getattr(request, "session", {}).keys()) if request else None,
            list(getattr(request, "data", {}).keys()) if request else None,
        )

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
