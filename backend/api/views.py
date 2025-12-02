import csv
import json
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.hashers import check_password
from django.db import models
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from rest_framework import permissions, status, viewsets
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


def format_decimal(value: Decimal) -> str:
    return f"{value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"


def calculate_ccf_breakdown(total: Decimal):
    base = (total / Decimal("1.13")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    debit = (base * Decimal("0.13")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    difference = total - (base + debit)
    if difference != Decimal("0"):
        debit += difference
    return base, debit


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
        if getattr(self, "action", None) == "list":
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


class InvoiceExportView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        export_type = (request.query_params.get("type") or "").lower()
        export_format = (request.query_params.get("format") or "csv").lower()

        if export_type not in {"consumidores", "contribuyentes"}:
            return Response(
                {"detail": "Parametro 'type' inválido. Usa consumidores o contribuyentes."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if export_format not in {"csv", "json", "xlsx"}:
            return Response(
                {"detail": "Parametro 'format' inválido. Usa csv, json o xlsx."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        invoices = Invoice.objects.select_related("client").prefetch_related("dte_records")
        invoices = filter_invoices_queryset(invoices, request.query_params)

        if export_type == "consumidores":
            invoices = invoices.filter(doc_type=Invoice.CF)
            dataset = self._build_cf_rows(invoices)
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
        else:
            invoices = invoices.filter(doc_type=Invoice.CCF)
            dataset = self._build_ccf_rows(invoices)
            headers = [
                "FECHA DE EMISION",
                "No. CORRELATIVO PREIMPRESO",
                "No. CONTROL INTERNO SISTEMA FORMULARIO UNICO",
                "NOMBRE DEL CLIENTE, MANDANTE O MANDATARIO",
                "NRC",
                "EXENTAS",
                "INTERNAS GRAVADAS",
                "DEBITO FISCAL",
                "EXENTAS (reserva)",
                "INTERNAS GRAVADAS (reserva)",
                "DEBITO FISCAL (reserva)",
                "IVA RETENIDO",
                "TOTAL",
            ]

        filename = f"libro-{export_type}-{timezone.now():%Y-%m}.{export_format}"

        if export_format == "json":
            return Response(dataset, headers={"Content-Disposition": f"attachment; filename={filename}"})
        if export_format == "csv":
            return self._export_csv(headers, dataset, filename)
        return self._export_xlsx(headers, dataset, filename)

    def _build_cf_rows(self, invoices):
        daily_totals = {}
        for invoice in invoices:
            total = Decimal(invoice.total or 0)
            daily_totals.setdefault(invoice.date, Decimal("0"))
            daily_totals[invoice.date] += total

        rows = []
        for invoice_date in sorted(daily_totals.keys()):
            total = daily_totals[invoice_date]
            rows.append(
                [
                    invoice_date.day,
                    "",
                    "",
                    "",
                    "0.00",
                    format_decimal(total),
                    "0.00",
                    format_decimal(total),
                    "0.00",
                    format_decimal(total),
                ]
            )
        return rows

    def _build_ccf_rows(self, invoices):
        rows = []
        for invoice in invoices:
            total = Decimal(invoice.total or 0)
            base, debit = calculate_ccf_breakdown(total)
            dte_record = invoice.dte_records.first()
            control_number = dte_record.control_number if dte_record else ""
            client = invoice.client
            rows.append(
                [
                    invoice.date.strftime("%d/%m/%Y"),
                    invoice.number,
                    control_number,
                    client.company_name or client.full_name,
                    client.nrc,
                    "0.00",
                    format_decimal(base),
                    format_decimal(debit),
                    "0.00",
                    "0.00",
                    "0.00",
                    "0.00",
                    format_decimal(total),
                ]
            )
        return rows

    def _export_csv(self, headers, dataset, filename):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = f"attachment; filename={filename}"
        writer = csv.writer(response)
        writer.writerow(headers)
        for row in dataset:
            writer.writerow(row)
        return response

    def _export_xlsx(self, headers, dataset, filename):
        wb = Workbook()
        ws = wb.active
        ws.append(headers)
        for row in dataset:
            ws.append(row)

        response = HttpResponse(
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = f"attachment; filename={filename}"
        wb.save(response)
        return response
