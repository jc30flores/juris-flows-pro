from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0009_issuer_profile_and_staff_rubro"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoiceitem",
            name="override_authorized_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="authorized_price_overrides",
                to="api.staffuser",
            ),
        ),
        migrations.AddField(
            model_name="invoiceitem",
            name="override_authorized_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
