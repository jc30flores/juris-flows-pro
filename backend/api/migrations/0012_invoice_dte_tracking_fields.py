from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0011_invoice_item_no_sujeta"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="estado_dte",
            field=models.CharField(
                choices=[("Aprobado", "Aprobado"), ("Pendiente", "Pendiente"), ("Rechazado", "Rechazado")],
                default="Pendiente",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="invoice",
            name="numero_control",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="invoice",
            name="codigo_generacion",
            field=models.CharField(blank=True, max_length=64, null=True),
        ),
        migrations.AddField(
            model_name="invoice",
            name="last_dte_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="invoice",
            name="dte_send_attempts",
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name="invoice",
            name="last_dte_error",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="invoice",
            name="last_dte_error_code",
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
