from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0015_invoiceitem_override_reason"),
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
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name='api_invoiceitem' AND column_name='override_authorized_by'
  ) THEN
    ALTER TABLE api_invoiceitem ALTER COLUMN override_authorized_by DROP NOT NULL;
    ALTER TABLE api_invoiceitem ALTER COLUMN override_authorized_by SET DEFAULT '';
    UPDATE api_invoiceitem SET override_authorized_by = '' WHERE override_authorized_by IS NULL;
  ELSE
    ALTER TABLE api_invoiceitem ADD COLUMN override_authorized_by text DEFAULT '' NULL;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name='api_invoiceitem' AND column_name='override_requested_by'
  ) THEN
    ALTER TABLE api_invoiceitem ALTER COLUMN override_requested_by DROP NOT NULL;
    ALTER TABLE api_invoiceitem ALTER COLUMN override_requested_by SET DEFAULT '';
    UPDATE api_invoiceitem SET override_requested_by = '' WHERE override_requested_by IS NULL;
  ELSE
    ALTER TABLE api_invoiceitem ADD COLUMN override_requested_by text DEFAULT '' NULL;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name='api_invoiceitem' AND column_name='override_expires_at'
  ) THEN
    ALTER TABLE api_invoiceitem ALTER COLUMN override_expires_at DROP NOT NULL;
    ALTER TABLE api_invoiceitem ALTER COLUMN override_expires_at DROP DEFAULT;
  ELSE
    ALTER TABLE api_invoiceitem ADD COLUMN override_expires_at timestamp with time zone NULL;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name='api_invoiceitem' AND column_name='override_code_used'
  ) THEN
    ALTER TABLE api_invoiceitem ALTER COLUMN override_code_used DROP NOT NULL;
    ALTER TABLE api_invoiceitem ALTER COLUMN override_code_used SET DEFAULT '';
    UPDATE api_invoiceitem SET override_code_used = '' WHERE override_code_used IS NULL;
  ELSE
    ALTER TABLE api_invoiceitem ADD COLUMN override_code_used text DEFAULT '' NULL;
  END IF;

  IF EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_name='api_invoiceitem' AND column_name='override_active'
  ) THEN
    UPDATE api_invoiceitem SET override_active = false WHERE override_active IS NULL;
    ALTER TABLE api_invoiceitem ALTER COLUMN override_active SET DEFAULT false;
    ALTER TABLE api_invoiceitem ALTER COLUMN override_active SET NOT NULL;
  ELSE
    ALTER TABLE api_invoiceitem ADD COLUMN override_active boolean DEFAULT false NOT NULL;
  END IF;
END $$;
""",
                    reverse_sql="SELECT 1;",
                )
            ],
            state_operations=[
                migrations.AddField(
                    model_name="invoiceitem",
                    name="override_authorized_by",
                    field=models.TextField(blank=True, default="", null=True),
                ),
                migrations.AddField(
                    model_name="invoiceitem",
                    name="override_requested_by",
                    field=models.TextField(blank=True, default="", null=True),
                ),
                migrations.AddField(
                    model_name="invoiceitem",
                    name="override_expires_at",
                    field=models.DateTimeField(blank=True, null=True),
                ),
                migrations.AddField(
                    model_name="invoiceitem",
                    name="override_code_used",
                    field=models.TextField(blank=True, default="", null=True),
                ),
                migrations.AddField(
                    model_name="invoiceitem",
                    name="override_active",
                    field=models.BooleanField(default=False),
                ),
            ],
        ),
    ]
