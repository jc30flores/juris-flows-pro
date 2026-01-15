from django.db import migrations


def normalize_invoice_statuses(apps, schema_editor):
    Invoice = apps.get_model("api", "Invoice")
    for invoice in Invoice.objects.all().only("id", "dte_status", "estado_dte"):
        updates = {}
        if invoice.dte_status:
            normalized = str(invoice.dte_status).upper()
            if invoice.dte_status != normalized:
                updates["dte_status"] = normalized
        if invoice.estado_dte:
            normalized = str(invoice.estado_dte).upper()
            if invoice.estado_dte != normalized:
                updates["estado_dte"] = normalized
        if updates:
            Invoice.objects.filter(id=invoice.id).update(**updates)


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0013_dterecord_rename_active_staffuser_is_active_and_more"),
    ]

    operations = [
        migrations.RunPython(normalize_invoice_statuses, migrations.RunPython.noop),
    ]
