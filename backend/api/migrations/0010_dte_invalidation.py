from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0009_invoice_dte_autoresend_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="DTEInvalidation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("invoice", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="dte_invalidations", to="api.invoice")),
                ("status", models.CharField(default="ENVIANDO", max_length=20)),
                ("hacienda_state", models.CharField(blank=True, default="", max_length=50)),
                ("request_payload", models.JSONField()),
                ("response_payload", models.JSONField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "api_dte_invalidation",
            },
        ),
        migrations.AddIndex(
            model_name="dteinvalidation",
            index=models.Index(fields=["status"], name="api_dte_in_status_0c8d29_idx"),
        ),
        migrations.AddIndex(
            model_name="dteinvalidation",
            index=models.Index(fields=["hacienda_state"], name="api_dte_in_haciend_8bb2b9_idx"),
        ),
        migrations.AddIndex(
            model_name="dteinvalidation",
            index=models.Index(fields=["created_at"], name="api_dte_in_created_c997c5_idx"),
        ),
    ]
