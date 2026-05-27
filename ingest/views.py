from django.db.models import Count, Sum
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .models import AuditEvent, EmissionRecord, IngestionBatch, Organization, SourceSystem
from .normalizers import (
    normalize_sap_row,
    normalize_travel_row,
    normalize_utility_row,
    parse_csv_upload,
    save_records,
)
from .serializers import AuditEventSerializer, BatchSerializer, EmissionRecordSerializer, SourceSystemSerializer


def current_org(request):
    slug = request.headers.get("X-Org-Slug") or request.query_params.get("org") or "acme-industrials"
    org, _ = Organization.objects.get_or_create(name="Acme Industrials", slug=slug)
    return org


def get_source(org, kind):
    defaults = {
        SourceSystem.SourceKind.SAP_ODATA: ("SAP S/4HANA Purchase Orders", "/sap/opu/odata/sap/API_PURCHASEORDER_PROCESS_SRV"),
        SourceSystem.SourceKind.UTILITY_CSV: ("Green Button Utility Portal CSV", "portal-export"),
        SourceSystem.SourceKind.CONCUR_EXPORT: ("SAP Concur Itinerary Export", "concur-itinerary-report"),
    }
    name, external_ref = defaults[kind]
    source, _ = SourceSystem.objects.get_or_create(
        organization=org,
        kind=kind,
        name=name,
        defaults={"external_ref": external_ref},
    )
    return source


@api_view(["GET"])
def health(_request):
    return Response({"ok": True})


@api_view(["GET"])
def dashboard(request):
    org = current_org(request)
    records = EmissionRecord.objects.filter(organization=org)
    by_status = {row["review_status"]: row["count"] for row in records.values("review_status").annotate(count=Count("id"))}
    by_scope = list(records.values("scope").annotate(count=Count("id"), co2e_kg=Sum("co2e_kg")).order_by("scope"))
    by_source = list(records.values("source_system__name").annotate(count=Count("id"), co2e_kg=Sum("co2e_kg")).order_by("source_system__name"))
    suspicious_count = sum(1 for record in records.only("suspicious_flags") if record.suspicious_flags)
    return Response(
        {
            "counts": {
                "total": records.count(),
                "pending": by_status.get(EmissionRecord.ReviewStatus.PENDING, 0),
                "needs_fix": by_status.get(EmissionRecord.ReviewStatus.NEEDS_FIX, 0),
                "approved": by_status.get(EmissionRecord.ReviewStatus.APPROVED, 0),
                "rejected": by_status.get(EmissionRecord.ReviewStatus.REJECTED, 0),
                "locked": by_status.get(EmissionRecord.ReviewStatus.LOCKED, 0),
                "suspicious": suspicious_count,
            },
            "by_scope": by_scope,
            "by_source": [
                {"source": item["source_system__name"], "count": item["count"], "co2e_kg": item["co2e_kg"]} for item in by_source
            ],
        }
    )


@api_view(["GET"])
def sources(request):
    org = current_org(request)
    for kind in SourceSystem.SourceKind.values:
        get_source(org, kind)
    return Response(SourceSystemSerializer(SourceSystem.objects.filter(organization=org), many=True).data)


@api_view(["GET"])
def batches(request):
    org = current_org(request)
    qs = IngestionBatch.objects.filter(organization=org).select_related("source_system").order_by("-received_at")[:20]
    return Response(BatchSerializer(qs, many=True).data)


@api_view(["GET"])
def records(request):
    org = current_org(request)
    qs = EmissionRecord.objects.filter(organization=org).select_related("facility", "batch", "source_system").order_by("-created_at")
    review_status = request.query_params.get("status")
    source_kind = request.query_params.get("source")
    if review_status:
        qs = qs.filter(review_status=review_status)
    if source_kind:
        qs = qs.filter(source_system__kind=source_kind)
    return Response(EmissionRecordSerializer(qs[:200], many=True).data)


def ingest_file(request, kind, normalizer):
    org = current_org(request)
    upload = request.FILES.get("file")
    if not upload:
        return Response({"detail": "Upload a CSV file as form field 'file'."}, status=status.HTTP_400_BAD_REQUEST)
    source = get_source(org, kind)
    batch = IngestionBatch.objects.create(organization=org, source_system=source, filename=upload.name)
    rows = parse_csv_upload(upload)
    created, failed = save_records(batch, rows, normalizer)
    return Response({"batch_id": batch.id, "rows": len(rows), "created": created, "failed": failed})


@api_view(["POST"])
def ingest_sap(request):
    return ingest_file(request, SourceSystem.SourceKind.SAP_ODATA, normalize_sap_row)


@api_view(["POST"])
def ingest_utility(request):
    return ingest_file(request, SourceSystem.SourceKind.UTILITY_CSV, normalize_utility_row)


@api_view(["POST"])
def ingest_travel(request):
    return ingest_file(request, SourceSystem.SourceKind.CONCUR_EXPORT, normalize_travel_row)


@api_view(["POST"])
def review_record(request, record_id):
    org = current_org(request)
    record = EmissionRecord.objects.get(organization=org, id=record_id)
    if record.review_status == EmissionRecord.ReviewStatus.LOCKED:
        return Response({"detail": "Locked records cannot be changed."}, status=status.HTTP_409_CONFLICT)

    action = request.data.get("action")
    actor = request.data.get("actor") or "analyst@breatheesg.com"
    before = {
        "review_status": record.review_status,
        "co2e_kg": str(record.co2e_kg) if record.co2e_kg is not None else None,
        "edits": record.edits,
    }

    if action == "approve":
        record.review_status = EmissionRecord.ReviewStatus.APPROVED
        record.approved_by = actor
        record.approved_at = timezone.now()
    elif action == "reject":
        record.review_status = EmissionRecord.ReviewStatus.REJECTED
    elif action == "lock":
        if record.review_status != EmissionRecord.ReviewStatus.APPROVED:
            return Response({"detail": "Only approved rows can be locked for audit."}, status=status.HTTP_400_BAD_REQUEST)
        record.review_status = EmissionRecord.ReviewStatus.LOCKED
        record.locked_at = timezone.now()
    elif action == "edit":
        edits = request.data.get("edits") or {}
        record.edits = {**record.edits, **edits}
        if "co2e_kg" in edits:
            record.co2e_kg = edits["co2e_kg"]
        record.review_status = EmissionRecord.ReviewStatus.PENDING
    else:
        return Response({"detail": "Action must be approve, reject, lock, or edit."}, status=status.HTTP_400_BAD_REQUEST)

    record.save()
    after = {
        "review_status": record.review_status,
        "co2e_kg": str(record.co2e_kg) if record.co2e_kg is not None else None,
        "edits": record.edits,
    }
    AuditEvent.objects.create(organization=org, record=record, actor=actor, action=action, before=before, after=after)
    return Response(EmissionRecordSerializer(record).data)


@api_view(["GET"])
def audit_events(request, record_id):
    org = current_org(request)
    qs = AuditEvent.objects.filter(organization=org, record_id=record_id)[:50]
    return Response(AuditEventSerializer(qs, many=True).data)
