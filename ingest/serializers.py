from rest_framework import serializers

from .models import AuditEvent, EmissionRecord, Facility, IngestionBatch, SourceSystem


class FacilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Facility
        fields = ["id", "code", "name", "country", "grid_region"]


class SourceSystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceSystem
        fields = ["id", "kind", "name", "external_ref", "metadata"]


class BatchSerializer(serializers.ModelSerializer):
    source_system = SourceSystemSerializer(read_only=True)

    class Meta:
        model = IngestionBatch
        fields = ["id", "source_system", "filename", "status", "row_count", "failed_count", "received_at", "processed_at", "notes"]


class EmissionRecordSerializer(serializers.ModelSerializer):
    facility = FacilitySerializer(read_only=True)
    batch_id = serializers.IntegerField(source="batch.id", read_only=True)
    source_name = serializers.CharField(source="source_system.name", read_only=True)
    source_kind = serializers.CharField(source="source_system.kind", read_only=True)

    class Meta:
        model = EmissionRecord
        fields = [
            "id",
            "batch_id",
            "source_name",
            "source_kind",
            "facility",
            "external_id",
            "source_payload",
            "edits",
            "activity_date",
            "period_start",
            "period_end",
            "scope",
            "category",
            "activity_type",
            "quantity",
            "unit",
            "normalized_quantity",
            "normalized_unit",
            "co2e_kg",
            "emission_factor_ref",
            "review_status",
            "suspicious_flags",
            "error_message",
            "approved_by",
            "approved_at",
            "locked_at",
            "created_at",
            "updated_at",
        ]


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ["id", "record_id", "actor", "action", "before", "after", "created_at"]
