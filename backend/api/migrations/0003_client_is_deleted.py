from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("api", "0002_activity_geodepartment_geomunicipality_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="is_deleted",
            field=models.BooleanField(default=False),
        ),
    ]
