from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0013_normalize_dte_status_values"),
    ]

    operations = [
        migrations.CreateModel(
            name="DTEInvalidation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(default="ENVIANDO", max_length=20)),
                ("codigo_generacion", models.CharField(max_length=64)),
                ("tipo_anulacion", models.IntegerField()),
                ("motivo_anulacion", models.TextField(blank=True, default="")),
                ("solicita_nombre", models.CharField(blank=True, default="", max_length=255)),
                ("solicita_tipo_doc", models.CharField(blank=True, default="", max_length=10)),
                ("solicita_num_doc", models.CharField(blank=True, default="", max_length=50)),
                ("responsable_nombre", models.CharField(blank=True, default="", max_length=255)),
                ("responsable_tipo_doc", models.CharField(blank=True, default="", max_length=10)),
                ("responsable_num_doc", models.CharField(blank=True, default="", max_length=50)),
                ("original_codigo_generacion", models.CharField(blank=True, default="", max_length=64)),
                ("original_numero_control", models.CharField(blank=True, default="", max_length=100)),
                ("original_sello_recibido", models.CharField(blank=True, default="", max_length=100)),
                ("original_tipo_dte", models.CharField(blank=True, default="", max_length=5)),
                ("original_fec_emi", models.CharField(blank=True, default="", max_length=20)),
                ("original_monto_iva", models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ("request_payload", models.JSONField()),
                ("response_payload", models.JSONField(blank=True, null=True)),
                ("hacienda_state", models.CharField(blank=True, default="", max_length=50)),
                ("error_message", models.TextField(blank=True, null=True)),
                ("error_code", models.CharField(blank=True, max_length=50, null=True)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "dte_record",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="invalidations",
                        to="api.DTERecord",
                    ),
                ),
                (
                    "invoice",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="dte_invalidations",
                        to="api.invoice",
                    ),
                ),
                (
                    "requested_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="dte_invalidations",
                        to="api.staffuser",
                    ),
                ),
            ],
            options={
                "db_table": "api_dte_invalidation",
                "indexes": [
                    models.Index(fields=["status"], name="api_dte_in_status_0a0361_idx"),
                    models.Index(fields=["codigo_generacion"], name="api_dte_in_codigo_2ab4b4_idx"),
                    models.Index(
                        fields=["original_codigo_generacion"],
                        name="api_dte_in_original_5152c7_idx",
                    ),
                    models.Index(
                        fields=["original_numero_control"],
                        name="api_dte_in_original_4f4b74_idx",
                    ),
                ],
            },
        ),
    ]
