from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0008_invoice_item_price_override_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoiceitem",
            name="override_reason",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="invoiceitem",
            name="override_authorized_by",
            field=models.CharField(blank=True, default="", max_length=150),
        ),
        migrations.AddField(
            model_name="invoiceitem",
            name="override_authorized_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
