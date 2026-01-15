from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0008_invoice_item_price_override_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="dte_send_attempts",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="invoice",
            name="last_dte_error",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="invoice",
            name="last_dte_error_code",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="invoice",
            name="last_dte_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="invoice",
            name="dte_is_sending",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="invoiceitem",
            name="original_unit_price",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                default=0,
                max_digits=12,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="invoiceitem",
            name="price_overridden",
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
        migrations.RunSQL(
            sql=(
                "UPDATE api_invoice SET dte_status='ACEPTADO' "
                "WHERE LOWER(dte_status) IN ('aprobado', 'aceptado');"
                "UPDATE api_invoice SET dte_status='PENDIENTE' "
                "WHERE LOWER(dte_status) IN ('pendiente');"
                "UPDATE api_invoice SET dte_status='RECHAZADO' "
                "WHERE LOWER(dte_status) IN ('rechazado');"
            ),
            reverse_sql=(
                "UPDATE api_invoice SET dte_status='Aprobado' "
                "WHERE dte_status='ACEPTADO';"
                "UPDATE api_invoice SET dte_status='Pendiente' "
                "WHERE dte_status='PENDIENTE';"
                "UPDATE api_invoice SET dte_status='Rechazado' "
                "WHERE dte_status='RECHAZADO';"
            ),
        ),
    ]
