from django.db import migrations, models


def backfill_has_credit_note(apps, schema_editor):
    Invoice = apps.get_model("api", "Invoice")
    Invoice.objects.filter(has_credit_note__isnull=True).update(has_credit_note=False)


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0005_invoice_credit_note_fields"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    "ALTER TABLE api_invoice ADD COLUMN IF NOT EXISTS has_credit_note boolean;"
                ),
                migrations.RunSQL(
                    "UPDATE api_invoice SET has_credit_note = FALSE WHERE has_credit_note IS NULL;"
                ),
                migrations.RunSQL(
                    "ALTER TABLE api_invoice ALTER COLUMN has_credit_note SET DEFAULT FALSE;"
                ),
                migrations.RunSQL(
                    "ALTER TABLE api_invoice ALTER COLUMN has_credit_note SET NOT NULL;"
                ),
            ],
            state_operations=[
                migrations.AddField(
                    model_name="invoice",
                    name="has_credit_note",
                    field=models.BooleanField(default=False),
                ),
            ],
        ),
        migrations.RunPython(backfill_has_credit_note, migrations.RunPython.noop),
    ]
