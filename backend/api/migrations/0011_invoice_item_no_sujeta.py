from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0010_invoice_item_override_audit"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoiceitem",
            name="is_no_sujeta",
            field=models.BooleanField(default=False),
        ),
    ]
