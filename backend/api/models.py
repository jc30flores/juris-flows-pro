import uuid

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

    APPROVED = "ACEPTADO"
    PENDING = "PENDIENTE"
    REJECTED = "RECHAZADO"
    INVALIDATED = "INVALIDADO"
    DTE_STATUS_CHOICES = [
        (APPROVED, "Aprobado"),
        (PENDING, "Pendiente"),
        (REJECTED, "Rechazado"),
        (INVALIDATED, "Invalidado"),
    ]

    number = models.CharField(max_length=50, unique=True)
    date = models.DateField()
    client = models.ForeignKey(Client, related_name="invoices", on_delete=models.PROTECT)
    doc_type = models.CharField(max_length=3, choices=DOC_TYPE_CHOICES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    dte_status = models.CharField(max_length=20, choices=DTE_STATUS_CHOICES)
    estado_dte = models.CharField(
        max_length=20,
        choices=DTE_STATUS_CHOICES,
        default=PENDING,
    )
    numero_control = models.CharField(max_length=100, blank=True, null=True)
    codigo_generacion = models.CharField(max_length=64, blank=True, null=True)
    last_dte_sent_at = models.DateTimeField(null=True, blank=True)
    dte_send_attempts = models.IntegerField(default=0)
    last_dte_error = models.TextField(null=True, blank=True)
    last_dte_error_code = models.CharField(max_length=50, null=True, blank=True)
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


class DTEControlCounter(models.Model):
    ambiente = models.CharField(max_length=2)
    tipo_dte = models.CharField(max_length=2)
    anio_emision = models.IntegerField()
    est_code = models.CharField(max_length=4)
    pv_code = models.CharField(max_length=4)
    last_number = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "dte_control_counters"
        unique_together = ("ambiente", "tipo_dte", "anio_emision", "est_code", "pv_code")
        indexes = [
            models.Index(fields=["ambiente", "tipo_dte", "anio_emision"]),
        ]

    def __str__(self) -> str:
        return (
            f"{self.ambiente}-{self.tipo_dte}-{self.anio_emision}-"
            f"{self.est_code}{self.pv_code}"
        )


class DTEInvalidation(models.Model):
    invoice = models.ForeignKey(
        "Invoice",
        on_delete=models.CASCADE,
        related_name="dte_invalidations",
    )
    dte_record = models.ForeignKey(
        "DTERecord",
        on_delete=models.SET_NULL,
        related_name="invalidations",
        null=True,
        blank=True,
    )
    requested_by = models.ForeignKey(
        "StaffUser",
        on_delete=models.SET_NULL,
        related_name="dte_invalidations",
        null=True,
        blank=True,
    )
    status = models.CharField(max_length=20, default="ENVIANDO")
    codigo_generacion = models.CharField(max_length=64)
    tipo_anulacion = models.IntegerField()
    motivo_anulacion = models.TextField(blank=True, default="")
    solicita_nombre = models.CharField(max_length=255, blank=True, default="")
    solicita_tipo_doc = models.CharField(max_length=10, blank=True, default="")
    solicita_num_doc = models.CharField(max_length=50, blank=True, default="")
    responsable_nombre = models.CharField(max_length=255, blank=True, default="")
    responsable_tipo_doc = models.CharField(max_length=10, blank=True, default="")
    responsable_num_doc = models.CharField(max_length=50, blank=True, default="")
    original_codigo_generacion = models.CharField(max_length=64, blank=True, default="")
    original_numero_control = models.CharField(max_length=100, blank=True, default="")
    original_sello_recibido = models.CharField(max_length=100, blank=True, default="")
    original_tipo_dte = models.CharField(max_length=5, blank=True, default="")
    original_fec_emi = models.CharField(max_length=20, blank=True, default="")
    original_monto_iva = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    request_payload = models.JSONField()
    response_payload = models.JSONField(null=True, blank=True)
    hacienda_state = models.CharField(max_length=50, blank=True, default="")
    error_message = models.TextField(null=True, blank=True)
    error_code = models.CharField(max_length=50, null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "api_dte_invalidation"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["codigo_generacion"]),
            models.Index(fields=["original_codigo_generacion"]),
            models.Index(fields=["original_numero_control"]),
        ]

    def __str__(self) -> str:
        return f"Invalidacion {self.codigo_generacion} ({self.status})"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice, related_name="items", on_delete=models.CASCADE
    )
    service = models.ForeignKey(Service, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    original_unit_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    price_overridden = models.BooleanField(default=False)
    is_no_sujeta = models.BooleanField(default=False)
    override_authorized_by = models.ForeignKey(
        "StaffUser",
        related_name="authorized_price_overrides",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    override_authorized_at = models.DateTimeField(null=True, blank=True)

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
    active_rubro_code = models.CharField(max_length=10, blank=True, default="")

    class Meta:
        db_table = "api_staffuser"

    def __str__(self):
        return self.full_name or self.username


class IssuerProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    rubro_code = models.CharField(max_length=10, unique=True)
    rubro_name = models.CharField(max_length=255)
    emisor_schema = models.JSONField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "api_issuer_profile"

    def __str__(self) -> str:
        return f"{self.rubro_code} - {self.rubro_name}"


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
