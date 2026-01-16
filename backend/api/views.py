import csv
import logging
from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.core import signing
from django.db import models
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.timezone import localtime
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

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
from .connectivity import get_connectivity_status
from .dte_cf_service import send_dte_for_invoice
from .dte_invalidation_service import (
    extract_invalidation_requirements,
    send_dte_invalidation,
)
from .dte_config import get_dte_base_url
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

PRICE_OVERRIDE_ACCESS_CODE = getattr(settings, "PRICE_OVERRIDE_ACCESS_CODE", "123")
PRICE_OVERRIDE_TOKEN_MAX_AGE = getattr(settings, "PRICE_OVERRIDE_TOKEN_MAX_AGE", 300)
PRICE_OVERRIDE_TOKEN_SALT = "price-override"

logger = logging.getLogger(__name__)


def _build_invalidation_response(
    *,
    ok: bool,
    status_label: str,
    message: str,
    http_status: int,
    details: dict | None = None,
):
    payload = {
        "ok": ok,
        "status": status_label,
        "message": message,
    }
    if details:
        payload["details"] = details
    return Response(payload, status=http_status)

def filter_invoices_queryset(queryset, params):
    search = params.get("search")
    date_filter = params.get("filter") or params.get("date_filter")
    client_id = params.get("client")
    doc_type = params.get("doc_type")
    payment_method = params.get("payment_method")
    dte_status = params.get("dte_status")
    start_date = params.get("start_date")
    end_date = params.get("end_date")

    if search:
        queryset = queryset.filter(
            Q(number__icontains=search)
            | Q(client__full_name__icontains=search)
            | Q(client__company_name__icontains=search)
        )

    if date_filter in {"today"}:
        today = timezone.localdate()
        queryset = queryset.filter(date=today)
    elif date_filter in {"week", "this-week"}:
        today = timezone.localdate()
        start_of_week = today - timedelta(days=today.weekday())
        queryset = queryset.filter(date__gte=start_of_week)
    elif date_filter in {"month", "this-month"}:
        today = timezone.localdate()
        start_of_month = today.replace(day=1)
        queryset = queryset.filter(date__gte=start_of_month)

    if start_date:
        queryset = queryset.filter(date__gte=start_date)
    if end_date:
        queryset = queryset.filter(date__lte=end_date)

    if client_id:
        queryset = queryset.filter(client_id=client_id)
    if doc_type:
        queryset = queryset.filter(doc_type=doc_type)
    if payment_method:
        queryset = queryset.filter(payment_method=payment_method)
    if dte_status:
        queryset = queryset.filter(dte_status__iexact=dte_status)

    return queryset


class InvoiceExportAllCSVAPIView(APIView):
    """
    GET /api/invoices/export/
    Descarga un CSV con todas las facturas.
    """

    def get(self, request, *args, **kwargs):
        dte_type = request.GET.get("dte_type")
        month = int(request.GET.get("month") or localtime(timezone.now()).month)
        year = int(request.GET.get("year") or localtime(timezone.now()).year)

        invoices = Invoice.objects.all()

        invoices = invoices.filter(date__year=year, date__month=month)

        if dte_type == "consumidores":
            invoices = invoices.filter(doc_type=Invoice.CF)
        elif dte_type == "contribuyentes":
            invoices = invoices.filter(doc_type=Invoice.CCF)

        invoices = invoices.order_by("id")

        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = 'attachment; filename="todas-las-ventas.csv"'

        writer = csv.writer(response)
        writer.writerow(
            [
                "NumeroFactura",
                "Fecha",
                "Cliente",
                "TipoDocumento",
                "MetodoPago",
                "EstadoDTE",
                "Total",
            ]
        )

        for inv in invoices:
            numero = getattr(inv, "number", getattr(inv, "invoice_number", inv.id))
            fecha_field = getattr(inv, "date", getattr(inv, "issue_date", None))
            if fecha_field:
                if isinstance(fecha_field, datetime):
                    fecha_dt = localtime(fecha_field)
                    fecha = fecha_dt.strftime("%Y-%m-%d")
                else:
                    fecha = fecha_field.strftime("%Y-%m-%d")
            else:
                fecha = ""
            cliente = getattr(getattr(inv, "client", None), "name", "") or ""
            tipo_doc = getattr(inv, "doc_type", getattr(inv, "type", ""))
            metodo = getattr(inv, "payment_method", "")
            estado_dte = getattr(inv, "dte_status", "")
            total = getattr(inv, "total", 0) or 0

            writer.writerow(
                [
                    numero,
                    fecha,
                    cliente,
                    tipo_doc,
                    metodo,
                    estado_dte,
                    f"{float(total):.2f}",
                ]
            )

        return response

class ServiceCategoryViewSet(viewsets.ModelViewSet):
    queryset = ServiceCategory.objects.all()
    serializer_class = ServiceCategorySerializer
    permission_classes = [permissions.AllowAny]


class ConnectivityStatusView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response(get_connectivity_status())


class PriceOverrideValidationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        code = request.data.get("code") or ""
        if code != PRICE_OVERRIDE_ACCESS_CODE:
            return Response(
                {"detail": "Código de acceso inválido."},
                status=status.HTTP_403_FORBIDDEN,
            )
        token = signing.dumps(
            {"authorized": True, "issued_at": timezone.now().isoformat()},
            salt=PRICE_OVERRIDE_TOKEN_SALT,
        )
        return Response(
            {"token": token, "expires_in": PRICE_OVERRIDE_TOKEN_MAX_AGE},
            status=status.HTTP_200_OK,
        )


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.select_related("category").all()
    serializer_class = ServiceSerializer
    permission_classes = [permissions.AllowAny]


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.filter(is_deleted=False)
    serializer_class = ClientSerializer
    permission_classes = [permissions.AllowAny]

    def perform_destroy(self, instance):
        instance.is_deleted = True
        instance.save(update_fields=["is_deleted"])


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = (
        Invoice.objects.select_related("client")
        .prefetch_related("items", "dte_records")
        .all()
    )
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, "action", None) in {"list"}:
            return filter_invoices_queryset(queryset, self.request.query_params)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        invoice = serializer.save()

        headers = self.get_success_headers(serializer.data)
        data = self.get_serializer(invoice).data

        dte_message = getattr(invoice, "_dte_message", None)
        if dte_message:
            data["dte_message"] = dte_message

        return Response(data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=["post"], url_path="resend-dte")
    def resend_dte(self, request, pk=None):
        invoice = self.get_object()
        if str(invoice.dte_status).upper() != Invoice.PENDING:
            return Response(
                {"detail": "Solo se permite reenviar DTEs en estado PENDIENTE."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if invoice.dte_is_sending:
            return Response(
                {"detail": "El DTE ya está siendo enviado."},
                status=status.HTTP_409_CONFLICT,
            )

        invoice.dte_is_sending = True
        invoice.save(update_fields=["dte_is_sending"])
        try:
            send_dte_for_invoice(
                invoice,
                force_now_timestamp=True,
                ensure_identifiers=True,
            )
        finally:
            invoice.dte_is_sending = False
            invoice.save(update_fields=["dte_is_sending"])

        serializer = self.get_serializer(invoice)
        data = serializer.data
        dte_message = getattr(invoice, "_dte_message", None)
        if dte_message:
            data["dte_message"] = dte_message
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="invalidate-dte")
    def invalidate_dte(self, request, pk=None):
        invoice = self.get_object()
        dte_base_url = get_dte_base_url()
        if not dte_base_url:
            return _build_invalidation_response(
                ok=False,
                status_label="CONFIG_FALTANTE",
                message=(
                    "DTE_BASE_URL no configurada. Configure la URL del puente DTE para invalidación."
                ),
                http_status=status.HTTP_503_SERVICE_UNAVAILABLE,
                details={"missing": ["DTE_BASE_URL"]},
            )
        normalized_status = str(invoice.dte_status or "").upper()
        if normalized_status == Invoice.INVALIDATED:
            return _build_invalidation_response(
                ok=False,
                status_label="BLOQUEADO",
                message="La factura ya está invalidada.",
                http_status=status.HTTP_409_CONFLICT,
            )
        if normalized_status != Invoice.APPROVED:
            return _build_invalidation_response(
                ok=False,
                status_label="BLOQUEADO",
                message="Solo DTE ACEPTADO puede invalidarse.",
                http_status=status.HTTP_409_CONFLICT,
            )

        record = invoice.dte_records.order_by("-created_at").first()
        if not record:
            return _build_invalidation_response(
                ok=False,
                status_label="BLOQUEADO",
                message="No existe DTERecord para esta factura.",
                http_status=status.HTTP_409_CONFLICT,
            )

        try:
            requirements = extract_invalidation_requirements(record)
        except ValueError as exc:
            logger.exception(
                "Invalidation payload parse failed invoice_id=%s", invoice.id, exc_info=exc
            )
            return _build_invalidation_response(
                ok=False,
                status_label="BLOQUEADO",
                message=str(exc),
                http_status=status.HTTP_409_CONFLICT,
            )
        missing_fields = [
            field
            for field in ("codigo_generacion", "numero_control", "sello_recibido", "fec_emi")
            if not requirements.get(field)
        ]
        if missing_fields:
            return _build_invalidation_response(
                ok=False,
                status_label="BLOQUEADO",
                message=f"Faltan datos para invalidar: {', '.join(missing_fields)}",
                http_status=status.HTTP_409_CONFLICT,
                details={"missing_fields": missing_fields},
            )

        logger.info(
            "DTE invalidation request invoice_id=%s dte_status=%s has_dte_record=%s "
            "has_codigo_generacion=%s has_numero_control=%s has_sello_recibido=%s has_fec_emi=%s "
            "ambiente=%s",
            invoice.id,
            normalized_status,
            True,
            bool(requirements.get("codigo_generacion")),
            bool(requirements.get("numero_control")),
            bool(requirements.get("sello_recibido")),
            bool(requirements.get("fec_emi")),
            requirements.get("ambiente"),
        )

        tipo_anulacion = request.data.get("tipoAnulacion") or request.data.get("tipo_anulacion")
        motivo_anulacion = request.data.get("motivoAnulacion") or request.data.get(
            "motivo_anulacion"
        )
        staff_user_id = request.data.get("staff_user_id")
        try:
            staff_user_id = int(staff_user_id) if staff_user_id is not None else None
        except (TypeError, ValueError):
            staff_user_id = None

        try:
            (
                invalidation,
                response_payload,
                http_status,
                result_status,
                detail,
                bridge_error,
            ) = send_dte_invalidation(
                invoice,
                tipo_anulacion=int(tipo_anulacion) if tipo_anulacion else 2,
                motivo_anulacion=motivo_anulacion or "",
                staff_user_id=staff_user_id,
            )
        except ValueError as exc:
            return _build_invalidation_response(
                ok=False,
                status_label="BLOQUEADO",
                message=str(exc),
                http_status=status.HTTP_409_CONFLICT,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Unexpected error invalidating invoice %s", invoice.id, exc_info=exc)
            return _build_invalidation_response(
                ok=False,
                status_label="ERROR_INTERNO",
                message="Error interno al construir/enviar invalidación.",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        ok_value = result_status in {"ACEPTADO", "PENDIENTE", "INVALIDADO"}
        details = {
            "invalidation_id": invalidation.id,
            "bridge": response_payload,
        }
        if bridge_error is not None:
            details["bridge_error"] = bridge_error
            details["bridge_url"] = bridge_error.get("bridge_url")
            details["bridge_status"] = bridge_error.get("bridge_status")
            details["bridge_body"] = bridge_error.get("bridge_body")

        status_label = "INVALIDADO" if result_status == "ACEPTADO" else result_status
        return _build_invalidation_response(
            ok=ok_value,
            status_label=status_label,
            message=detail,
            http_status=http_status,
            details=details,
        )


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


class LoginView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        username = request.data.get("username", "")
        password = request.data.get("password", "")
        user = StaffUser.objects.filter(username=username, is_active=True).first()
        if not user or not check_password(password, user.password):
            return Response({"detail": "Credenciales inválidas."}, status=400)
        return Response(
            {
                "id": user.id,
                "full_name": user.full_name,
                "username": user.username,
                "role": user.role,
            }
        )


class LogoutView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


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
