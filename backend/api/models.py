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
    phone = models.CharField(max_length=30, blank=True)
    email = models.EmailField(blank=True)
    department_code = models.CharField(max_length=4, blank=True, null=True)
    municipality_code = models.CharField(max_length=4, blank=True, null=True)
    activity_code = models.CharField(max_length=10, blank=True, null=True)

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
    total = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.number


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
    ADMIN = "ADMIN"
    COLABORADOR = "COLABORADOR"
    CONTADOR = "CONTADOR"
    ROLE_CHOICES = [
        (ADMIN, "Admin"),
        (COLABORADOR, "Colaborador"),
        (CONTADOR, "Contador"),
    ]

    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.name} ({self.role})"


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
