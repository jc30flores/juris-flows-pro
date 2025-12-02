import csv
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.hashers import check_password
from django.db import models
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.utils.timezone import localtime
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


class InvoiceExportAllCSVAPIView(APIView):
    """
    GET /api/invoices/export/?type=consumidores|contribuyentes&format=csv|json|xlsx&month=MM&year=YYYY
    Exporta libros de ventas por mes con descarga directa.
    """

    def get(self, request, *args, **kwargs):
        export_type = request.GET.get("type", "consumidores")
        export_format = request.GET.get("format", "csv")
        month = int(request.GET.get("month") or localtime().month)
        year = int(request.GET.get("year") or localtime().year)

        if export_type not in ("consumidores", "contribuyentes"):
            return Response({"detail": "type inválido"}, status=400)
        if export_format not in ("csv", "json", "xlsx"):
            return Response({"detail": "format inválido"}, status=400)

        invoices = (
            Invoice.objects.select_related("client")
            .filter(date__year=year, date__month=month)
            .order_by("date", "id")
        )

        if export_type == "consumidores":
            invoices = invoices.filter(doc_type=Invoice.CF)
        else:
            invoices = invoices.filter(doc_type=Invoice.CCF)

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
            for inv in invoices:
                day = inv.date.day
                key = day
                number = inv.number
                total = Decimal(inv.total or 0)
                if key not in grouped:
                    grouped[key] = {
                        "day": day,
                        "from": number,
                        "to": number,
                        "total": total,
                    }
                else:
                    grouped[key]["from"] = min(str(grouped[key]["from"]), str(number))
                    grouped[key]["to"] = max(str(grouped[key]["to"]), str(number))
                    grouped[key]["total"] += total

            rows = []
            for key in sorted(grouped.keys()):
                entry = grouped[key]
                total = entry["total"].quantize(Decimal("0.01"))
                rows.append(
                    [
                        entry["day"],
                        entry["from"],
                        entry["to"],
                        "",
                        "0.00",
                        f"{total:.2f}",
                        "0.00",
                        f"{total:.2f}",
                        "0.00",
                        f"{total:.2f}",
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
            for inv in invoices:
                issued = inv.date.strftime("%d/%m/%Y")
                total = Decimal(inv.total or 0).quantize(Decimal("0.01"))
                base = (total / Decimal("1.13")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                debit = (total - base).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                rows.append(
                    [
                        issued,
                        inv.number,
                        inv.number,
                        getattr(inv.client, "company_name", "")
                        or getattr(inv.client, "full_name", "")
                        or "",
                        getattr(inv.client, "nrc", ""),
                        "0.00",
                        f"{base:.2f}",
                        f"{debit:.2f}",
                        "0.00",
                        "0.00",
                        "0.00",
                        "0.00",
                        f"{total:.2f}",
                    ]
                )

        filename = f"libro-{export_type}-{year:04d}-{month:02d}"

        if export_format == "json":
            from json import dumps

            data = {"headers": headers, "rows": rows}
            response = HttpResponse(
                dumps(data),
                content_type="application/json; charset=utf-8",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}.json"'
            return response

        if export_format == "xlsx":
            try:
                from openpyxl import Workbook
            except ImportError:
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
