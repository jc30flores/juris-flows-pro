from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0003_client_is_deleted"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="dte_codigo_generacion",
            field=models.CharField(blank=True, default="", max_length=100, null=True),
        ),
        migrations.AddField(
            model_name="invoice",
            name="dte_numero_control",
            field=models.CharField(blank=True, default="", max_length=100, null=True),
        ),
    ]
