from django.db import migrations


def normalize_dte_status(apps, schema_editor):
    Invoice = apps.get_model("api", "Invoice")
    if not hasattr(Invoice, "dte_status"):
        return

    for invoice in Invoice.objects.all().only("id", "dte_status", "estado_dte"):
        updates = []
        for field_name in ("dte_status", "estado_dte"):
            current_value = getattr(invoice, field_name, None)
            if not current_value:
                continue
            normalized = current_value.strip().lower()
            if normalized in {"aprobado", "aceptado"}:
                new_value = "ACEPTADO"
            elif normalized == "pendiente":
                new_value = "PENDIENTE"
            elif normalized == "rechazado":
                new_value = "RECHAZADO"
            else:
                new_value = current_value.strip().upper()
            if current_value != new_value:
                setattr(invoice, field_name, new_value)
                updates.append(field_name)
        if updates:
            invoice.save(update_fields=updates)


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0012_invoice_dte_tracking_fields"),
    ]

    operations = [
        migrations.RunPython(normalize_dte_status, migrations.RunPython.noop),
    ]
