from django.db import migrations, models


def populate_original_unit_price(apps, schema_editor):
    InvoiceItem = apps.get_model("api", "InvoiceItem")
    for item in InvoiceItem.objects.all():
        item.original_unit_price = item.unit_price
        item.price_overridden = False
        item.save(update_fields=["original_unit_price", "price_overridden"])


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0007_dte_control_counter"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoiceitem",
            name="original_unit_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="invoiceitem",
            name="price_overridden",
            field=models.BooleanField(default=False),
        ),
        migrations.RunPython(populate_original_unit_price, migrations.RunPython.noop),
    ]
