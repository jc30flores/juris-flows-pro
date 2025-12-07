import csv
import logging
from datetime import date, datetime, timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.db import models
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.timezone import localtime
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
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
from .dte_cf_service import (
    invalidate_dte_for_invoice,
    send_ccf_credit_note_for_invoice,
)


def _parse_date_param(value):
    if not value:
        return None

    try:
        if "T" in value:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return timezone.localdate(parsed)
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None
from .connectivity import get_connectivity_status
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

logger = logging.getLogger(__name__)


class InvoicePagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 100


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

    parsed_start_date = _parse_date_param(start_date)
    parsed_end_date = _parse_date_param(end_date)

    if parsed_start_date:
        queryset = queryset.filter(date__gte=parsed_start_date)
    if parsed_end_date:
        queryset = queryset.filter(date__lte=parsed_end_date)

    if client_id:
        queryset = queryset.filter(client_id=client_id)
    if doc_type:
        queryset = queryset.filter(doc_type=doc_type)
    if payment_method:
        queryset = queryset.filter(payment_method=payment_method)
    if dte_status:
        queryset = queryset.filter(dte_status=dte_status)

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
        .prefetch_related("items")
        .all()
        .order_by("-created_at", "-id")
    )
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = InvoicePagination

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, "action", None) in {"list"}:
            filtered = filter_invoices_queryset(queryset, self.request.query_params)
            return filtered.order_by("-created_at", "-id")
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

    @action(detail=True, methods=["post"], url_path="invalidate")
    def invalidate(self, request, pk=None):
        invoice = self.get_object()

        if invoice.doc_type not in {Invoice.CF, Invoice.SX}:
            return Response(
                {"detail": "Solo se pueden invalidar facturas CF o SX."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        record = (
            invoice.dte_records.filter(dte_type__in=["CF", "SE"])
            .order_by("-created_at")
            .first()
        )

        if not record:
            return Response(
                {"detail": "No existe DTE para invalidar esta factura."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            dte_status, response_data = invalidate_dte_for_invoice(invoice, record)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error invalidando DTE", exc_info=exc)
            return Response(
                {"detail": "Error al invalidar DTE en Hacienda."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        success = dte_status == Invoice.INVALIDATED
        message = (
            "DTE invalidado correctamente" if success else "No se pudo invalidar el DTE"
        )
        return Response(
            {
                "success": success,
                "message": message,
                "detail": message,
                "dte_status": dte_status,
                "response": response_data,
            },
            status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST,
        )

    @action(detail=True, methods=["post"], url_path="credit-note")
    def credit_note(self, request, pk=None):
        invoice = self.get_object()

        if invoice.doc_type != Invoice.CCF:
            return Response(
                {"detail": "Solo se pueden generar notas de crédito para facturas CCF."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not invoice.items.exists():
            return Response(
                {"detail": "La factura no tiene items para generar la nota de crédito."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        accepted_states = {"ACEPTADO", "APROBADO", "PROCESADO", "RECIBIDO"}
        if invoice.has_credit_note and (
            (invoice.credit_note_status or "").upper() in accepted_states
        ):
            return Response(
                {
                    "detail": "Esta factura ya tiene una Nota de Crédito aceptada. No se puede emitir otra.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        existing_nc = invoice.dte_records.filter(
            dte_type__in=["05", "NC"],
            status__in=accepted_states,
        ).exists()

        existing_nc_hacienda = invoice.dte_records.filter(
            dte_type__in=["05", "NC"],
            hacienda_state__in=["PROCESADO", "RECIBIDO", "ACEPTADO", "APROBADO"],
        ).exists()

        if existing_nc or existing_nc_hacienda:
            return Response(
                {
                    "detail": "Esta factura ya tiene una Nota de Crédito aceptada. No se puede emitir otra.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            record = send_ccf_credit_note_for_invoice(invoice)
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Error enviando nota de crédito", exc_info=exc)
            return Response(
                {"detail": "Error al generar nota de crédito."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        invoice.refresh_from_db(fields=["dte_status", "has_credit_note", "credit_note_status"])

        credit_note_state_upper = (getattr(invoice, "credit_note_status", "") or "").upper()
        success = bool(invoice.has_credit_note and credit_note_state_upper in accepted_states)
        message = (
            getattr(invoice, "_dte_message", None)
            or ("Nota de crédito (CCF) enviada correctamente" if success else None)
            or "No se pudo enviar la nota de crédito"
        )

        return Response(
            {
                "success": success,
                "message": message,
                "detail": message,
                "dte_status": getattr(invoice, "dte_status", None),
                "has_credit_note": getattr(invoice, "has_credit_note", False),
                "credit_note_status": getattr(invoice, "credit_note_status", None),
                "response": getattr(record, "response_payload", None),
            },
            status=status.HTTP_200_OK if success else status.HTTP_400_BAD_REQUEST,
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


class PriceOverrideValidationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        code = request.data.get("code", "")
        if code == settings.PRICE_OVERRIDE_CODE:
            return Response({"valid": True}, status=status.HTTP_200_OK)
        return Response(
            {"valid": False, "detail": "Código de acceso inválido."},
            status=status.HTTP_403_FORBIDDEN,
        )
