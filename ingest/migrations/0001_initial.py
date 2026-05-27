# Generated for the Breathe ESG prototype.

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=180)),
                ("slug", models.SlugField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name="Facility",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=60)),
                ("name", models.CharField(max_length=180)),
                ("country", models.CharField(default="US", max_length=2)),
                ("grid_region", models.CharField(blank=True, max_length=60)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="facilities", to="ingest.organization")),
            ],
            options={"unique_together": {("organization", "code")}},
        ),
        migrations.CreateModel(
            name="SourceSystem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("sap_odata", "SAP OData"), ("utility_csv", "Utility CSV"), ("concur_export", "Concur Export")], max_length=40)),
                ("name", models.CharField(max_length=180)),
                ("external_ref", models.CharField(blank=True, max_length=180)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sources", to="ingest.organization")),
            ],
            options={"unique_together": {("organization", "kind", "name")}},
        ),
        migrations.CreateModel(
            name="IngestionBatch",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("filename", models.CharField(blank=True, max_length=240)),
                ("status", models.CharField(choices=[("received", "Received"), ("processed", "Processed"), ("failed", "Failed")], default="received", max_length=20)),
                ("row_count", models.PositiveIntegerField(default=0)),
                ("failed_count", models.PositiveIntegerField(default=0)),
                ("received_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("processed_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="batches", to="ingest.organization")),
                ("source_system", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="batches", to="ingest.sourcesystem")),
            ],
        ),
        migrations.CreateModel(
            name="EmissionRecord",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("external_id", models.CharField(max_length=180)),
                ("source_hash", models.CharField(max_length=64)),
                ("source_row_number", models.PositiveIntegerField(default=0)),
                ("source_payload", models.JSONField(default=dict)),
                ("edits", models.JSONField(blank=True, default=dict)),
                ("activity_date", models.DateField(blank=True, null=True)),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(blank=True, null=True)),
                ("scope", models.CharField(choices=[("scope_1", "Scope 1"), ("scope_2", "Scope 2"), ("scope_3", "Scope 3")], max_length=20)),
                ("category", models.CharField(choices=[("stationary_combustion", "Stationary combustion"), ("purchased_electricity", "Purchased electricity"), ("business_travel", "Business travel"), ("purchased_goods", "Purchased goods")], max_length=60)),
                ("activity_type", models.CharField(max_length=120)),
                ("quantity", models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True)),
                ("unit", models.CharField(max_length=30)),
                ("normalized_quantity", models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True)),
                ("normalized_unit", models.CharField(max_length=30)),
                ("co2e_kg", models.DecimalField(blank=True, decimal_places=4, max_digits=14, null=True)),
                ("emission_factor_ref", models.CharField(blank=True, max_length=160)),
                ("review_status", models.CharField(choices=[("pending", "Pending"), ("needs_fix", "Needs fix"), ("approved", "Approved"), ("rejected", "Rejected"), ("locked", "Locked")], default="pending", max_length=20)),
                ("suspicious_flags", models.JSONField(blank=True, default=list)),
                ("error_message", models.TextField(blank=True)),
                ("approved_by", models.CharField(blank=True, max_length=180)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("locked_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("batch", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="records", to="ingest.ingestionbatch")),
                ("facility", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="records", to="ingest.facility")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="records", to="ingest.organization")),
                ("source_system", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="records", to="ingest.sourcesystem")),
            ],
            options={
                "indexes": [
                    models.Index(fields=["organization", "review_status"], name="ingest_emis_organiz_96a3e4_idx"),
                    models.Index(fields=["organization", "scope", "category"], name="ingest_emis_organiz_b0a6f2_idx"),
                    models.Index(fields=["source_system", "external_id"], name="ingest_emis_source__0fd032_idx"),
                ],
                "unique_together": {("organization", "source_system", "source_hash")},
            },
        ),
        migrations.CreateModel(
            name="AuditEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor", models.CharField(max_length=180)),
                ("action", models.CharField(max_length=60)),
                ("before", models.JSONField(blank=True, default=dict)),
                ("after", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="ingest.organization")),
                ("record", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="audit_events", to="ingest.emissionrecord")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
