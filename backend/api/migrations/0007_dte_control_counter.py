from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0006_invoice_has_credit_note_default"),
    ]

    operations = [
        migrations.CreateModel(
            name="DTEControlCounter",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ambiente", models.CharField(max_length=2)),
                ("tipo_dte", models.CharField(max_length=2)),
                ("anio_emision", models.IntegerField()),
                ("est_code", models.CharField(max_length=4)),
                ("pv_code", models.CharField(max_length=4)),
                ("last_number", models.IntegerField(default=0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "dte_control_counters",
                "unique_together": {("ambiente", "tipo_dte", "anio_emision", "est_code", "pv_code")},
            },
        ),
        migrations.AddIndex(
            model_name="dtecontrolcounter",
            index=models.Index(fields=["ambiente", "tipo_dte", "anio_emision"], name="dte_contro_ambiente_83e0ee_idx"),
        ),
    ]
