from django.contrib import admin

from .models import AuditEvent, EmissionRecord, Facility, IngestionBatch, Organization, SourceSystem


admin.site.register([Organization, Facility, SourceSystem, IngestionBatch, EmissionRecord, AuditEvent])
