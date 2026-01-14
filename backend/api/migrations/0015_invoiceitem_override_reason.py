from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0014_merge_20260113_0255"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql="""
DO $$
BEGIN
  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name='api_invoiceitem' AND column_name='override_reason'
  ) THEN
    ALTER TABLE api_invoiceitem ALTER COLUMN override_reason DROP NOT NULL;
    ALTER TABLE api_invoiceitem ALTER COLUMN override_reason SET DEFAULT '';
    UPDATE api_invoiceitem SET override_reason = '' WHERE override_reason IS NULL;
  ELSE
    ALTER TABLE api_invoiceitem ADD COLUMN override_reason text DEFAULT '' NULL;
    UPDATE api_invoiceitem SET override_reason = '' WHERE override_reason IS NULL;
  END IF;
END $$;
""",
                    reverse_sql="SELECT 1;",
                )
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
