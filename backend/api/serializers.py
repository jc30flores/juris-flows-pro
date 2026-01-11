import logging
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
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
PRICE_OVERRIDE_TOKEN_MAX_AGE = int(
    getattr(settings, "PRICE_OVERRIDE_TOKEN_MAX_AGE", 300)
)
PRICE_OVERRIDE_TOKEN_SALT = getattr(
    settings,
    "PRICE_OVERRIDE_TOKEN_SALT",
    "price-override",
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

        normalized_items = self._normalize_items_payload(items_data, services_data)
        if normalized_items:
            validated_data["total"] = self._calculate_total(normalized_items)

        invoice = super().create(validated_data)
        self._upsert_items(invoice, normalized_items or [], replace=True)
        try:
            if invoice.doc_type == Invoice.CF:
                send_cf_dte_for_invoice(invoice)
            elif invoice.doc_type == Invoice.CCF:
                send_ccf_dte_for_invoice(invoice)
            elif invoice.doc_type == Invoice.SX:
                send_se_dte_for_invoice(invoice)
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

        if not validated_data.get("dte_status"):
            validated_data["dte_status"] = instance.dte_status or Invoice.PENDING

        normalized_items = None
        if services_data is not None or items_data is not None:
            normalized_items = self._normalize_items_payload(items_data, services_data)
            validated_data["total"] = self._calculate_total(normalized_items)

        invoice = super().update(instance, validated_data)

        if normalized_items is not None:
            self._upsert_items(invoice, normalized_items, replace=True)

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
                Decimal(str(original_unit_price))
                if original_unit_price is not None
                else unit_price
            )

            if unit_price <= 0:
                raise serializers.ValidationError(
                    {"services": f"El precio debe ser mayor a 0 para servicio {service_id}."}
                )

            price_overridden = unit_price != original_unit_price
            override_token = self._get_override_token(service_data)
            override_reason = service_data.get("override_reason") or service_data.get(
                "overrideReason"
            )
            if price_overridden:
                if not self._is_price_override_authorized(
                    override_code=override_code,
                    override_token=override_token,
                ):
                    self._log_override_denied(
                        service_id=service_id,
                        unit_price=unit_price,
                        original_unit_price=original_unit_price,
                    )
                    raise PermissionDenied(
                        "Se requiere autorización para modificar el precio del "
                        f"servicio {service_id}."
                    )

            subtotal = self._coerce_subtotal(
                unit_price=unit_price,
                quantity=quantity,
            )

            normalized_items.append(
                {
                    "service_id": service_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "original_unit_price": original_unit_price,
                    "subtotal": subtotal,
                    "price_overridden": price_overridden,
                    "override_reason": override_reason or "",
                    "override_authorized_at": timezone.now()
                    if price_overridden
                    else None,
                    "override_authorized_by": self._get_override_authorizer()
                    if price_overridden
                    else "",
                }
            )

        return normalized_items

    def _normalize_items_payload(self, items_data, services_data):
        if services_data is not None:
            return self._normalize_services(services_data)
        if not items_data:
            return []

        normalized_items = []
        for item_data in items_data:
            service_id = item_data.get("service_id") or item_data.get("service")
            if not service_id:
                continue
            quantity = item_data.get("quantity", 1)
            unit_price = Decimal(str(item_data.get("unit_price") or 0))
            original_unit_price = item_data.get("original_unit_price")
            if original_unit_price is None:
                service_instance = Service.objects.filter(pk=service_id).first()
                original_unit_price = (
                    service_instance.base_price if service_instance else unit_price
                )
            original_unit_price = Decimal(str(original_unit_price))

            if unit_price <= 0:
                raise serializers.ValidationError(
                    {"items": f"El precio debe ser mayor a 0 para servicio {service_id}."}
                )

            price_overridden = unit_price != original_unit_price
            override_code = item_data.get("override_code") or item_data.get("overrideCode")
            override_token = self._get_override_token(item_data)
            override_reason = item_data.get("override_reason") or item_data.get(
                "overrideReason"
            )
            if price_overridden and not self._is_price_override_authorized(
                override_code=override_code,
                override_token=override_token,
            ):
                self._log_override_denied(
                    service_id=service_id,
                    unit_price=unit_price,
                    original_unit_price=original_unit_price,
                )
                raise PermissionDenied(
                    "Se requiere autorización para modificar el precio del "
                    f"servicio {service_id}."
                )

            normalized_items.append(
                {
                    "service_id": service_id,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "original_unit_price": original_unit_price,
                    "subtotal": self._coerce_subtotal(unit_price, quantity),
                    "price_overridden": price_overridden,
                    "override_reason": override_reason or "",
                    "override_authorized_at": timezone.now()
                    if price_overridden
                    else None,
                    "override_authorized_by": self._get_override_authorizer()
                    if price_overridden
                    else "",
                }
            )

        return normalized_items

    def _coerce_subtotal(self, unit_price, quantity):
        subtotal = Decimal(unit_price) * Decimal(int(quantity))
        return subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _calculate_total(self, items):
        total = sum(
            ((item.get("subtotal") or Decimal("0")) for item in items),
            Decimal("0"),
        )
        return Decimal(total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _get_override_token(self, payload):
        if isinstance(payload, dict):
            token = payload.get("override_token") or payload.get("overrideToken")
            if token:
                return token
        request = self.context.get("request")
        if not request:
            return None
        header_token = request.headers.get("X-Price-Override-Token") if hasattr(
            request, "headers"
        ) else None
        if header_token:
            return header_token
        return request.data.get("override_token") if hasattr(request, "data") else None

    def _is_price_override_authorized(self, override_code, override_token):
        if override_code and override_code == PRICE_OVERRIDE_ACCESS_CODE:
            return True
        if not override_token:
            return False
        signer = TimestampSigner(salt=PRICE_OVERRIDE_TOKEN_SALT)
        try:
            signer.unsign(override_token, max_age=PRICE_OVERRIDE_TOKEN_MAX_AGE)
        except (BadSignature, SignatureExpired):
            return False
        return True

    def _get_override_authorizer(self):
        request = self.context.get("request")
        if request and getattr(request, "user", None) and request.user.is_authenticated:
            return getattr(request.user, "username", None) or str(request.user)
        return "override_token"

    def _log_override_denied(self, service_id, unit_price, original_unit_price):
        if not settings.DEBUG:
            return
        request = self.context.get("request")
        logger.debug(
            "Price override denied for service %s. unit_price=%s original_unit_price=%s user=%s auth=%s",
            service_id,
            unit_price,
            original_unit_price,
            getattr(request, "user", None),
            getattr(request, "auth", None),
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
