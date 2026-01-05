from django.db import models


class ServiceCategory(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.name


class Service(models.Model):
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        ServiceCategory, related_name="services", on_delete=models.PROTECT
    )
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


class Client(models.Model):
    CF = "CF"
    CCF = "CCF"
    SX = "SX"
    CLIENT_TYPE_CHOICES = [
        (CF, "Consumidor Final"),
        (CCF, "Crédito Fiscal"),
        (SX, "Sujeto Excluido"),
    ]

    full_name = models.CharField(max_length=200)
    company_name = models.CharField(max_length=200, blank=True)
    client_type = models.CharField(max_length=3, choices=CLIENT_TYPE_CHOICES)
    dui = models.CharField(max_length=25, blank=True)
    nit = models.CharField(max_length=25, blank=True)
    nrc = models.CharField(max_length=10, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    direccion = models.TextField(blank=True, default="")
    department_code = models.CharField(max_length=4, blank=True, null=True)
    municipality_code = models.CharField(max_length=4, blank=True, null=True)
    activity_code = models.CharField(max_length=10, blank=True, null=True)
    activity_description = models.CharField(max_length=255, blank=True, default="")
    is_deleted = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.company_name or self.full_name


class Invoice(models.Model):
    CF = "CF"
    CCF = "CCF"
    SX = "SX"
    DOC_TYPE_CHOICES = [
        (CF, "Consumidor Final"),
        (CCF, "Crédito Fiscal"),
        (SX, "Sujeto Excluido"),
    ]

    CASH = "Efectivo"
    CARD = "Tarjeta"
    TRANSFER = "Transferencia"
    CHECK = "Cheque"
    PAYMENT_METHOD_CHOICES = [
        (CASH, "Efectivo"),
        (CARD, "Tarjeta"),
        (TRANSFER, "Transferencia"),
        (CHECK, "Cheque"),
    ]

    APPROVED = "Aprobado"
    PENDING = "Pendiente"
    REJECTED = "Rechazado"
    DTE_STATUS_CHOICES = [
        (APPROVED, "Aprobado"),
        (PENDING, "Pendiente"),
        (REJECTED, "Rechazado"),
    ]

    number = models.CharField(max_length=50, unique=True)
    date = models.DateField()
    client = models.ForeignKey(Client, related_name="invoices", on_delete=models.PROTECT)
    doc_type = models.CharField(max_length=3, choices=DOC_TYPE_CHOICES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    dte_status = models.CharField(max_length=20, choices=DTE_STATUS_CHOICES)
    observations = models.TextField(blank=True, default="")
    has_credit_note = models.BooleanField(default=False)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.number


class DTERecord(models.Model):
    # Relación con la factura interna
    invoice = models.ForeignKey(
        "Invoice",
        on_delete=models.CASCADE,
        related_name="dte_records",
    )

    # Datos clave del DTE
    dte_type = models.CharField(max_length=20)
    status = models.CharField(max_length=20, default="PENDIENTE")

    # Identificadores importantes para buscar rápido
    control_number = models.CharField(max_length=100, blank=True, default="")
    hacienda_uuid = models.CharField(max_length=100, blank=True, default="")
    hacienda_state = models.CharField(max_length=50, blank=True, default="")

    # Datos clave de emisor / receptor / monto
    issuer_nit = models.CharField(max_length=32, blank=True, default="")
    receiver_nit = models.CharField(max_length=32, blank=True, default="")
    receiver_name = models.CharField(max_length=255, blank=True, default="")
    issue_date = models.DateField(null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # JSON completo enviado y recibido
    request_payload = models.JSONField()
    response_payload = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "api_dte_record"
        indexes = [
            models.Index(fields=["dte_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["control_number"]),
            models.Index(fields=["hacienda_uuid"]),
            models.Index(fields=["issue_date"]),
            models.Index(fields=["receiver_nit"]),
        ]

    def __str__(self):
        return f"DTE {self.id} - {self.dte_type} - {self.status}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice, related_name="items", on_delete=models.CASCADE
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def __str__(self) -> str:
        return f"{self.invoice.number} - {self.service.name}"


class Expense(models.Model):
    name = models.CharField(max_length=200)
    provider = models.CharField(max_length=200)
    date = models.DateField()
    total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.name} - {self.provider}"

class StaffUser(models.Model):
    full_name = models.CharField(max_length=255, default="", blank=True)
    username = models.CharField(max_length=150, unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "api_staffuser"

    def __str__(self):
        return self.full_name or self.username


class GeoDepartment(models.Model):
    code = models.CharField(max_length=2, primary_key=True)
    name = models.TextField()
    normalized = models.TextField()
    updated_at = models.DateTimeField()
    version = models.IntegerField()

    class Meta:
        db_table = "geo_departments"
        managed = False
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class GeoMunicipality(models.Model):
    id = models.IntegerField(primary_key=True)
    dept_code = models.CharField(max_length=4)
    muni_code = models.CharField(max_length=4)
    name = models.TextField()
    normalized = models.TextField()
    updated_at = models.DateTimeField()
    version = models.IntegerField()

    class Meta:
        db_table = "geo_municipalities"
        managed = False
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Activity(models.Model):
    code = models.CharField(max_length=10, primary_key=True)
    description = models.TextField()
    normalized = models.TextField()
    updated_at = models.DateTimeField()
    version = models.IntegerField()

    class Meta:
        db_table = "activities_catalog"
        managed = False
        ordering = ["description"]

    def __str__(self) -> str:
        return f"{self.code} - {self.description}"
