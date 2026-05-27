from django.urls import path

from . import views


urlpatterns = [
    path("health/", views.health),
    path("dashboard/", views.dashboard),
    path("sources/", views.sources),
    path("batches/", views.batches),
    path("records/", views.records),
    path("records/<int:record_id>/review/", views.review_record),
    path("records/<int:record_id>/audit/", views.audit_events),
    path("ingest/sap/", views.ingest_sap),
    path("ingest/utility/", views.ingest_utility),
    path("ingest/travel/", views.ingest_travel),
]
