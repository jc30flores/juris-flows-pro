from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0004_invoice_dte_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoice",
            name="credit_note_status",
            field=models.CharField(blank=True, max_length=30, null=True),
        ),
        migrations.AddField(
            model_name="invoice",
            name="has_credit_note",
            field=models.BooleanField(default=False),
        ),
    ]

