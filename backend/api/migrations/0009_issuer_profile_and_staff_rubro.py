from django.db import migrations, models
import uuid


def seed_issuer_profiles(apps, schema_editor):
    IssuerProfile = apps.get_model("api", "IssuerProfile")

    base_emisor = {
        "nit": "12172402231026",
        "nrc": "3255304",
        "nombre": "EDWIN ARNULFO MATA CASTILLO",
        "nombreComercial": "RELITE GROUP",
        "direccion": {
            "municipio": "22",
            "complemento": "AV. BARCELONA POLIGONO B, RESIDENCIAL SEVILLA, #21, SAN MIGUEL",
            "departamento": "12",
        },
        "telefono": "77961054",
        "correo": "infodte@relitegroup.com",
        "codEstable": "M001",
        "codPuntoVenta": "P001",
        "codPuntoVentaMH": "P001",
        "codEstableMH": "M001",
        "tipoEstablecimiento": "02",
    }

    rubros = [
        {
            "code": "68200",
            "name": "Actividades Inmobiliarias Realizadas a Cambio de una Retribucion o por Contrata",
        },
        {
            "code": "64922",
            "name": "Tipos de Creditos N.C.P",
        },
        {
            "code": "45100",
            "name": "Venta de Vehiculos Automotores.",
        },
    ]

    for rubro in rubros:
        schema = {
            **base_emisor,
            "codActividad": rubro["code"],
            "descActividad": rubro["name"],
        }
        IssuerProfile.objects.update_or_create(
            rubro_code=rubro["code"],
            defaults={
                "rubro_name": rubro["name"],
                "emisor_schema": schema,
                "is_active": True,
            },
        )


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0008_invoice_item_price_override_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="staffuser",
            name="active_rubro_code",
            field=models.CharField(blank=True, default="", max_length=10),
        ),
        migrations.CreateModel(
            name="IssuerProfile",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("rubro_code", models.CharField(max_length=10, unique=True)),
                ("rubro_name", models.CharField(max_length=255)),
                ("emisor_schema", models.JSONField()),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "db_table": "api_issuer_profile",
            },
        ),
        migrations.RunPython(seed_issuer_profiles, reverse_code=migrations.RunPython.noop),
    ]
