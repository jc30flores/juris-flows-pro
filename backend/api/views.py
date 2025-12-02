import csv
import json
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

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

try:
    from openpyxl import Workbook
except ImportError:  # pragma: no cover - handled gracefully at runtime
    Workbook = None

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
        queryset = queryset.filter(dte_status=dte_status)

    return queryset


def _quantize_money(value: Decimal) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def build_cf_book(qs):
    headers = [
        "Día",
        "Del No",
        "Al No",
        "No. de Maq. Registradora",
        "Ventas Exentas",
        "Ventas Gravadas Locales",
        "Exportaciones",
        "Total Ventas",
        "Venta por Cuenta de Terceros",
        "Venta Total",
    ]

    grouped = {}
    for invoice in qs.order_by("date", "number"):
        grouped.setdefault(invoice.date, []).append(invoice)

    rows = []
    for invoice_date in sorted(grouped.keys()):
        invoices = grouped[invoice_date]
        totals = sum(
            ((invoice.total or Decimal("0")) for invoice in invoices),
            start=Decimal("0"),
        )
        ventas_gravadas = _quantize_money(totals)
        total_ventas = ventas_gravadas

        rows.append(
            [
                invoice_date.day,
                min(inv.number for inv in invoices),
                max(inv.number for inv in invoices),
                "",
                Decimal("0.00"),
                ventas_gravadas,
                Decimal("0.00"),
                total_ventas,
                Decimal("0.00"),
                total_ventas,
            ]
        )

    return headers, rows


def build_ccf_book(qs):
    headers = [
        "FECHA DE EMISION",
        "No. CORRELATIVO PREIMPRESO",
        "No. CONTROL INTERNO SISTEMA FORMULARIO UNICO",
        "NOMBRE DEL CLIENTE, MANDANTE O MANDATARIO",
        "NRC",
        "EXENTAS",
        "INTERNAS GRAVADAS",
        "DEBITO FISCAL",
        "EXENTAS",
        "INTERNAS GRAVADAS",
        "DEBITO FISCAL",
        "IVA RETENIDO",
        "TOTAL",
    ]

    rows = []
    for invoice in qs.order_by("date", "number"):
        total = _quantize_money(invoice.total)
        base = _quantize_money(total / Decimal("1.13"))
        debito = _quantize_money(total - base)
        diff = total - (base + debito)
        if diff:
            debito = _quantize_money(debito + diff)

        client_name = invoice.client.company_name or invoice.client.full_name
        nrc = invoice.client.nrc or ""

        rows.append(
            [
                invoice.date.strftime("%d/%m/%Y"),
                invoice.number,
                invoice.id,
                client_name,
                nrc,
                Decimal("0.00"),
                base,
                debito,
                Decimal("0.00"),
                Decimal("0.00"),
                Decimal("0.00"),
                Decimal("0.00"),
                total,
            ]
        )

    return headers, rows


class InvoiceExportAPIView(APIView):
    """
    GET /api/invoices/export/?type=consumidores|contribuyentes&format=csv|json|xlsx&month=MM&year=YYYY
    Exporta libros de ventas por mes.
    """

    def get(self, request, *args, **kwargs):
        export_type = (request.GET.get("type") or "consumidores").lower()
        export_format = (request.GET.get("format") or "csv").lower()
        now_local = localtime(timezone.now())

        try:
            month = int(request.GET.get("month") or now_local.month)
            year = int(request.GET.get("year") or now_local.year)
        except (TypeError, ValueError):
            return Response({"detail": "Parámetros inválidos"}, status=400)

        if export_type not in {"consumidores", "contribuyentes"}:
            return Response({"detail": "type inválido"}, status=400)
        if export_format not in {"csv", "json", "xlsx"}:
            return Response({"detail": "format inválido"}, status=400)
        if month < 1 or month > 12:
            return Response({"detail": "Parámetros inválidos"}, status=400)

        qs = Invoice.objects.all()
        qs = qs.filter(date__year=year, date__month=month)

        if export_type == "consumidores":
            qs = qs.filter(doc_type=Invoice.CF)
        else:
            qs = qs.filter(doc_type=Invoice.CCF)

        if export_type == "consumidores":
            headers = [
                "Día",
                "Del No",
                "Al No",
                "No. de Maq. Registradora",
                "Ventas Exentas",
                "Ventas Gravadas Locales",
                "Exportaciones",
                "Total Ventas",
                "Venta por Cuenta de Terceros",
                "Venta Total",
            ]
            grouped = {}
            for invoice in qs:
                day = invoice.date.day
                if day not in grouped:
                    grouped[day] = {
                        "day": day,
                        "from": invoice.number,
                        "to": invoice.number,
                        "total": Decimal(invoice.total or 0),
                    }
                    continue

                current = grouped[day]
                current["from"] = min(str(current["from"]), str(invoice.number))
                current["to"] = max(str(current["to"]), str(invoice.number))
                current["total"] += Decimal(invoice.total or 0)

            rows = []
            for day in sorted(grouped.keys()):
                data = grouped[day]
                total_value = data["total"].quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                rows.append(
                    [
                        data["day"],
                        data["from"],
                        data["to"],
                        "",
                        "0.00",
                        f"{total_value:.2f}",
                        "0.00",
                        f"{total_value:.2f}",
                        "0.00",
                        f"{total_value:.2f}",
                    ]
                )
        else:
            headers = [
                "FECHA DE EMISION",
                "No. CORRELATIVO PREIMPRESO",
                "No. CONTROL INTERNO SISTEMA FORMULARIO UNICO",
                "NOMBRE DEL CLIENTE, MANDANTE O MANDATARIO",
                "NRC",
                "EXENTAS",
                "INTERNAS GRAVADAS",
                "DEBITO FISCAL",
                "EXENTAS",
                "INTERNAS GRAVADAS",
                "DEBITO FISCAL",
                "IVA RETENIDO",
                "TOTAL",
            ]
            rows = []
            for invoice in qs.order_by("date", "id"):
                issued = invoice.date.strftime("%d/%m/%Y")
                correlativo = invoice.number
                control_interno = invoice.number
                client = getattr(invoice, "client", None)
                client_name = ""
                client_nrc = ""
                if client:
                    client_name = client.company_name or client.full_name
                    client_nrc = client.nrc or ""

                total = Decimal(invoice.total or 0).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                base = (total / Decimal("1.13")).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                debito = (total - base).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                diff = total - (base + debito)
                if diff:
                    debito = (debito + diff).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )

                rows.append(
                    [
                        issued,
                        correlativo,
                        control_interno,
                        client_name,
                        client_nrc,
                        "0.00",
                        f"{base:.2f}",
                        f"{debito:.2f}",
                        "0.00",
                        "0.00",
                        "0.00",
                        "0.00",
                        f"{total:.2f}",
                    ]
                )

        filename = f"libro-{export_type}-{year}-{month}"

        if export_format == "json":
            data = {"headers": headers, "rows": rows}
            response = HttpResponse(
                json.dumps(data),
                content_type="application/json; charset=utf-8",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}.json"'
            return response

        if export_format == "xlsx":
            if Workbook is None:
                return Response({"detail": "openpyxl no instalado"}, status=500)
            wb = Workbook()
            ws = wb.active
            ws.append(headers)
            for row in rows:
                ws.append(row)
            from io import BytesIO

            buffer = BytesIO()
            wb.save(buffer)
            buffer.seek(0)
            response = HttpResponse(
                buffer.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}.xlsx"'
            return response

        from io import StringIO

        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(row)
        response = HttpResponse(
            buffer.getvalue(),
            content_type="text/csv; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}.csv"'
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
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.AllowAny]


class InvoiceViewSet(viewsets.ModelViewSet):
    queryset = Invoice.objects.select_related("client").prefetch_related("items").all()
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()
        if getattr(self, "action", None) in {"list", "export"}:
            return filter_invoices_queryset(queryset, self.request.query_params)
        return queryset

    @action(detail=False, methods=["get"], url_path="export")
    def export(self, request, *args, **kwargs):
        export_type = (request.query_params.get("type") or "").lower()
        export_format = (request.query_params.get("format") or "csv").lower()
        month_param = request.query_params.get("month")
        year_param = request.query_params.get("year")

        if export_format == "excel":
            export_format = "xlsx"

        if export_type not in {"consumidores", "contribuyentes"}:
            return Response({"detail": "Parámetros inválidos"}, status=400)

        if export_format not in {"csv", "json", "xlsx"}:
            return Response({"detail": "Parámetros inválidos"}, status=400)

        today = timezone.localdate()
        try:
            month = int(month_param) if month_param is not None else today.month
            year = int(year_param) if year_param is not None else today.year
        except (TypeError, ValueError):
            return Response({"detail": "Parámetros inválidos"}, status=400)

        if month < 1 or month > 12:
            return Response({"detail": "Parámetros inválidos"}, status=400)

        qs = self.filter_queryset(self.get_queryset())
        qs = qs.filter(date__year=year, date__month=month)

        if export_type == "consumidores":
            qs = qs.filter(doc_type=Invoice.CF)
            headers, rows = build_cf_book(qs)
        elif export_type == "contribuyentes":
            qs = qs.filter(doc_type=Invoice.CCF)
            headers, rows = build_ccf_book(qs)
        else:
            return Response({"detail": "Parámetros inválidos"}, status=400)

        filename = f"libro-{export_type}-{year}-{month:02d}"

        if export_format == "csv":
            response = HttpResponse(
                content_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": f"attachment; filename=\"{filename}.csv\""
                },
            )
            writer = csv.writer(response)
            writer.writerow(headers)
            writer.writerows(rows)
            return response

        if export_format == "json":
            return Response({"headers": headers, "rows": rows}, status=200)

        wb = Workbook()
        ws = wb.active
        ws.append(headers)
        for row in rows:
            ws.append(row)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=\"{filename}.xlsx\""
            },
        )
        wb.save(response)
        return response

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
