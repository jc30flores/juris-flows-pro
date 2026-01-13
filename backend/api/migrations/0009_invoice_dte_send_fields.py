from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0008_invoice_item_price_override_fields"),
    ]

    operations = [
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
    ]
