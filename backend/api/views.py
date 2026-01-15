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
from rest_framework.response import Response
from rest_framework.views import APIView

from .dte_cf_service import send_dte_for_invoice
from .dte_invalidation_service import (
    get_invalidation_preview,
    invalidate_dte_for_invoice,
)
from .models import (
    Activity,
    Client,
    Expense,
    GeoDepartment,
    GeoMunicipality,
    IssuerProfile,
    Invoice,
    InvoiceItem,
    Service,
    ServiceCategory,
    StaffUser,
)
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
from .utils import generate_price_override_token, get_staff_user_from_request

logger = logging.getLogger(__name__)


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


def _resend_invoice_dte(invoice: Invoice, staff_user: StaffUser | None) -> Response:
    current_status = (invoice.dte_status or "").upper()
    if current_status != "PENDIENTE":
        return Response(
            {"detail": "El DTE solo puede reenviarse cuando está en PENDIENTE."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    send_dte_for_invoice(invoice, staff_user=staff_user, force_now_timestamp=True)
    invoice.refresh_from_db()

    data = InvoiceSerializer(invoice).data
    dte_message = getattr(invoice, "_dte_message", None)
    if dte_message:
        data["dte_message"] = dte_message

    response_status = status.HTTP_200_OK
    if getattr(invoice, "_dte_pending_due_to_api_down", False):
        response_status = status.HTTP_202_ACCEPTED

    return Response(data, status=response_status)


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
        staff_user = get_staff_user_from_request(request)
        serializer = self.get_serializer(
            data=request.data,
            context={"request": request, "staff_user": staff_user},
        )
        serializer.is_valid(raise_exception=True)

        invoice = serializer.save()

        headers = self.get_success_headers(serializer.data)
        data = self.get_serializer(invoice).data

        dte_message = getattr(invoice, "_dte_message", None)
        if dte_message:
            data["dte_message"] = dte_message

        response_status = status.HTTP_201_CREATED
        if getattr(invoice, "_dte_pending_due_to_api_down", False):
            response_status = status.HTTP_202_ACCEPTED

        return Response(data, status=response_status, headers=headers)

    @action(detail=True, methods=["post"], url_path="resend-dte")
    def resend_dte(self, request, pk=None):
        staff_user = get_staff_user_from_request(request)
        invoice = self.get_object()
        return _resend_invoice_dte(invoice, staff_user)

    @action(detail=True, methods=["get"], url_path="invalidation-preview")
    def invalidation_preview(self, request, pk=None):
        invoice = self.get_object()
        try:
            preview = get_invalidation_preview(invoice)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(preview)


class ResendDTEView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        invoice_id = request.data.get("invoice_id")
        if not invoice_id:
            return Response(
                {"detail": "invoice_id es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            invoice = Invoice.objects.get(id=invoice_id)
        except Invoice.DoesNotExist:
            return Response(
                {"detail": "Factura no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        staff_user = get_staff_user_from_request(request)
        return _resend_invoice_dte(invoice, staff_user)


class DTEInvalidateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        invoice_id = request.data.get("invoice_id")
        if not invoice_id:
            return Response(
                {"ok": False, "message": "invoice_id es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            invoice = Invoice.objects.select_related("client").get(id=invoice_id)
        except Invoice.DoesNotExist:
            return Response(
                {"ok": False, "message": "Factura no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        current_status = (invoice.dte_status or "").upper()
        if current_status == Invoice.INVALIDATED:
            return Response(
                {"ok": False, "message": "La factura ya está invalidada."},
                status=status.HTTP_409_CONFLICT,
            )
        if current_status != Invoice.APPROVED:
            return Response(
                {
                    "ok": False,
                    "message": "Solo se puede invalidar un DTE aceptado por Hacienda.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        tipo_anulacion = request.data.get("tipo_anulacion") or request.data.get("tipoAnulacion")
        if tipo_anulacion is None:
            return Response(
                {"ok": False, "message": "tipo_anulacion es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            tipo_anulacion_value = int(tipo_anulacion)
        except (TypeError, ValueError):
            return Response(
                {"ok": False, "message": "tipo_anulacion debe ser numérico."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        motivo = request.data.get("motivo") or request.data.get("motivo_anulacion") or ""
        staff_user = get_staff_user_from_request(request)

        try:
            invalidation, message = invalidate_dte_for_invoice(
                invoice,
                staff_user=staff_user,
                tipo_anulacion=tipo_anulacion_value,
                motivo_anulacion=motivo,
            )
        except ValueError as exc:
            return Response({"ok": False, "message": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:  # pragma: no cover - defensive
            logger.exception("Error invalidating DTE (invoice_id=%s)", invoice_id)
            return Response(
                {
                    "ok": False,
                    "message": "Ocurrió un error inesperado al invalidar el DTE.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response_data = {
            "ok": True,
            "invalidation_id": invalidation.id,
            "status": invalidation.status,
            "hacienda_state": invalidation.hacienda_state,
            "message": message,
            "codigo_generacion": invalidation.codigo_generacion,
        }
        response_status = status.HTTP_200_OK
        if invalidation.status == "PENDIENTE":
            response_status = status.HTTP_202_ACCEPTED
        return Response(response_data, status=response_status)


class EmisorRubrosView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        staff_user = get_staff_user_from_request(request)
        rubros = list(
            IssuerProfile.objects.filter(is_active=True)
            .order_by("rubro_code")
            .values("rubro_code", "rubro_name")
        )
        active_code = staff_user.active_rubro_code if staff_user else ""
        active_name = ""
        for rubro in rubros:
            if rubro["rubro_code"] == active_code:
                active_name = rubro["rubro_name"]
                break

        if not active_code and rubros:
            default_rubro = next(
                (rubro for rubro in rubros if rubro["rubro_code"] == "64922"),
                rubros[0],
            )
            active_code = default_rubro["rubro_code"]
            active_name = default_rubro["rubro_name"]
            if staff_user:
                staff_user.active_rubro_code = active_code
                staff_user.save(update_fields=["active_rubro_code"])

        return Response(
            {
                "rubros": [
                    {"code": rubro["rubro_code"], "name": rubro["rubro_name"]}
                    for rubro in rubros
                ],
                "active_rubro_code": active_code,
                "active_rubro_name": active_name,
            }
        )


class EmisorActiveRubroView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        staff_user = get_staff_user_from_request(request)
        if not staff_user:
            return Response(
                {"detail": "Usuario no identificado para asignar rubro."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        rubro_code = request.data.get("rubro_code")
        if not rubro_code:
            return Response(
                {"detail": "Debe enviar el rubro_code."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        profile = IssuerProfile.objects.filter(
            rubro_code=rubro_code,
            is_active=True,
        ).first()
        if not profile:
            return Response(
                {"detail": "Rubro no permitido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        staff_user.active_rubro_code = profile.rubro_code
        staff_user.save(update_fields=["active_rubro_code"])
        return Response(
            {
                "ok": True,
                "active_rubro_code": profile.rubro_code,
                "active_rubro_name": profile.rubro_name,
            }
        )


class EmisorActiveView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        staff_user = get_staff_user_from_request(request)
        rubro_code = staff_user.active_rubro_code if staff_user else ""
        profile = None
        if rubro_code:
            profile = IssuerProfile.objects.filter(
                rubro_code=rubro_code, is_active=True
            ).first()
        if not profile:
            profile = (
                IssuerProfile.objects.filter(rubro_code="64922", is_active=True).first()
                or IssuerProfile.objects.filter(is_active=True)
                .order_by("rubro_code")
                .first()
            )
        if not profile:
            return Response({"detail": "No hay perfiles de emisor configurados."}, status=404)
        if staff_user and staff_user.active_rubro_code != profile.rubro_code:
            staff_user.active_rubro_code = profile.rubro_code
            staff_user.save(update_fields=["active_rubro_code"])
        return Response(
            {
                "active_rubro_code": profile.rubro_code,
                "active_rubro_name": profile.rubro_name,
                "emisor_schema": profile.emisor_schema,
            }
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


class PriceOverrideValidateView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        access_code = request.data.get("code") or request.data.get("access_code")
        staff_user = get_staff_user_from_request(request)

        if access_code != settings.PRICE_OVERRIDE_ACCESS_CODE:
            if settings.DEBUG:
                logger.warning(
                    "Price override access denied (staff_user=%s, code_present=%s)",
                    getattr(staff_user, "id", None),
                    bool(access_code),
                )
            return Response(
                {"detail": "Código de acceso inválido."},
                status=status.HTTP_403_FORBIDDEN,
            )

        token = generate_price_override_token(staff_user)
        expires_in = getattr(settings, "PRICE_OVERRIDE_TOKEN_MAX_AGE_SECONDS", 300)
        return Response(
            {"override_token": token, "expires_in": expires_in},
            status=status.HTTP_200_OK,
        )


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
