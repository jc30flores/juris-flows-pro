from django.db import migrations, models


def backfill_invoice_item_prices(apps, schema_editor):
    InvoiceItem = apps.get_model("api", "InvoiceItem")
    for item in InvoiceItem.objects.all():
        unit_price = item.unit_price or 0
        subtotal = item.subtotal or 0
        if item.unit_price_snapshot is None:
            item.unit_price_snapshot = unit_price
        if item.applied_unit_price in (None, 0):
            item.applied_unit_price = unit_price
        if item.line_subtotal in (None, 0):
            item.line_subtotal = subtotal
        if not item.price_type:
            item.price_type = "UNIT"
        item.save(
            update_fields=[
                "unit_price_snapshot",
                "applied_unit_price",
                "line_subtotal",
                "price_type",
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0009_invoice_dte_autoresend_fields"),
    ]

    operations = [
        migrations.RenameField(
            model_name="service",
            old_name="base_price",
            new_name="unit_price",
        ),
        migrations.AddField(
            model_name="service",
            name="wholesale_price",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=10, null=True
            ),
        ),
        migrations.RenameField(
            model_name="invoiceitem",
            old_name="original_unit_price",
            new_name="unit_price_snapshot",
        ),
        migrations.AddField(
            model_name="invoiceitem",
            name="wholesale_price_snapshot",
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True
            ),
        ),
        migrations.AddField(
            model_name="invoiceitem",
            name="price_type",
            field=models.CharField(
                choices=[("UNIT", "Unitario"), ("WHOLESALE", "Mayoreo")],
                default="UNIT",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="invoiceitem",
            name="applied_unit_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.AddField(
            model_name="invoiceitem",
            name="line_subtotal",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=12),
        ),
        migrations.RunPython(backfill_invoice_item_prices, migrations.RunPython.noop),
    ]
