from django.db import migrations, models


def add_or_update_override_reason(apps, schema_editor):
    InvoiceItem = apps.get_model("api", "InvoiceItem")
    table_name = InvoiceItem._meta.db_table
    field = InvoiceItem._meta.get_field("override_reason")

    with schema_editor.connection.cursor() as cursor:
        columns = [
            column.name
            for column in schema_editor.connection.introspection.get_table_description(
                cursor, table_name
            )
        ]

    if "override_reason" not in columns:
        schema_editor.add_field(InvoiceItem, field)
        return

    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute(
            f"ALTER TABLE {table_name} ALTER COLUMN override_reason DROP NOT NULL;"
        )
        schema_editor.execute(
            f"ALTER TABLE {table_name} ALTER COLUMN override_reason SET DEFAULT '';"
        )
        return

    try:
        schema_editor.execute(
            f"ALTER TABLE {table_name} ALTER COLUMN override_reason DROP NOT NULL;"
        )
    except Exception:  # pragma: no cover - best effort on non-postgres
        return


def noop_reverse(apps, schema_editor):
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0014_merge_20260113_0255"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(add_or_update_override_reason, noop_reverse)
            ],
            state_operations=[
                migrations.AddField(
                    model_name="invoiceitem",
                    name="override_reason",
                    field=models.TextField(blank=True, default="", null=True),
                )
            ],
        ),
    ]
