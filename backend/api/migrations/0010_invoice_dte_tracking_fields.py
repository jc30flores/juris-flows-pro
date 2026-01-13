from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0009_invoice_dte_send_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="numero_control",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="invoice",
            name="codigo_generacion",
            field=models.CharField(blank=True, max_length=100, null=True),
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
