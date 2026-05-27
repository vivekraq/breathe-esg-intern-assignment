from django.db import models
from django.utils import timezone


class Organization(models.Model):
    name = models.CharField(max_length=180)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Facility(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="facilities")
    code = models.CharField(max_length=60)
    name = models.CharField(max_length=180)
    country = models.CharField(max_length=2, default="US")
    grid_region = models.CharField(max_length=60, blank=True)

    class Meta:
        unique_together = [("organization", "code")]

    def __str__(self):
        return f"{self.code} - {self.name}"


class SourceSystem(models.Model):
    class SourceKind(models.TextChoices):
        SAP_ODATA = "sap_odata", "SAP OData"
        UTILITY_CSV = "utility_csv", "Utility CSV"
        CONCUR_EXPORT = "concur_export", "Concur Export"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="sources")
    kind = models.CharField(max_length=40, choices=SourceKind.choices)
    name = models.CharField(max_length=180)
    external_ref = models.CharField(max_length=180, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [("organization", "kind", "name")]

    def __str__(self):
        return f"{self.organization.slug}:{self.name}"


class IngestionBatch(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        PROCESSED = "processed", "Processed"
        FAILED = "failed", "Failed"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="batches")
    source_system = models.ForeignKey(SourceSystem, on_delete=models.PROTECT, related_name="batches")
    filename = models.CharField(max_length=240, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    row_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    received_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.source_system.name} {self.received_at:%Y-%m-%d %H:%M}"


class EmissionRecord(models.Model):
    class Scope(models.TextChoices):
        SCOPE_1 = "scope_1", "Scope 1"
        SCOPE_2 = "scope_2", "Scope 2"
        SCOPE_3 = "scope_3", "Scope 3"

    class Category(models.TextChoices):
        STATIONARY_COMBUSTION = "stationary_combustion", "Stationary combustion"
        PURCHASED_ELECTRICITY = "purchased_electricity", "Purchased electricity"
        BUSINESS_TRAVEL = "business_travel", "Business travel"
        PURCHASED_GOODS = "purchased_goods", "Purchased goods"

    class ReviewStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        NEEDS_FIX = "needs_fix", "Needs fix"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        LOCKED = "locked", "Locked"

    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="records")
    batch = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name="records")
    source_system = models.ForeignKey(SourceSystem, on_delete=models.PROTECT, related_name="records")
    facility = models.ForeignKey(Facility, on_delete=models.SET_NULL, null=True, blank=True, related_name="records")
    external_id = models.CharField(max_length=180)
    source_hash = models.CharField(max_length=64)
    source_row_number = models.PositiveIntegerField(default=0)
    source_payload = models.JSONField(default=dict)
    edits = models.JSONField(default=dict, blank=True)
    activity_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    scope = models.CharField(max_length=20, choices=Scope.choices)
    category = models.CharField(max_length=60, choices=Category.choices)
    activity_type = models.CharField(max_length=120)
    quantity = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    unit = models.CharField(max_length=30)
    normalized_quantity = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    normalized_unit = models.CharField(max_length=30)
    co2e_kg = models.DecimalField(max_digits=14, decimal_places=4, null=True, blank=True)
    emission_factor_ref = models.CharField(max_length=160, blank=True)
    review_status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    suspicious_flags = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)
    approved_by = models.CharField(max_length=180, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    locked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["organization", "review_status"]),
            models.Index(fields=["organization", "scope", "category"]),
            models.Index(fields=["source_system", "external_id"]),
        ]
        unique_together = [("organization", "source_system", "source_hash")]

    def __str__(self):
        return f"{self.external_id} {self.review_status}"


class AuditEvent(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="audit_events")
    record = models.ForeignKey(EmissionRecord, on_delete=models.CASCADE, related_name="audit_events")
    actor = models.CharField(max_length=180)
    action = models.CharField(max_length=60)
    before = models.JSONField(default=dict, blank=True)
    after = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
