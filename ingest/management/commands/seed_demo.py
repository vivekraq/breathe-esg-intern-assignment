from django.core.management.base import BaseCommand

from ingest.models import Facility, Organization, SourceSystem
from ingest.normalizers import normalize_sap_row, normalize_travel_row, normalize_utility_row, save_records
from ingest.models import IngestionBatch


SAP_ROWS = [
    {"Einkaufsbeleg": "4500102871", "Item": "10", "Werk": "DE01", "Belegdatum": "15.01.2026", "Material": "DIESEL-BULK", "Menge": "1200", "MEINS": "L"},
    {"Einkaufsbeleg": "4500102910", "Item": "20", "Werk": "US02", "Belegdatum": "2026-01-20", "Material Description": "Gasoline fleet card", "Quantity": "410", "Unit": "gal"},
    {"Einkaufsbeleg": "4500103112", "Item": "10", "Werk": "ZZ99", "Belegdatum": "02/04/2026", "Material": "Office furniture", "Menge": "8", "MEINS": "EA"},
]

UTILITY_ROWS = [
    {"Account Number": "DE01", "Meter Number": "MTR-7781", "Service Start": "2026-01-12", "Service End": "2026-02-11", "Usage (kWh)": "84200", "Unit": "kWh", "Tariff": "TOU-Large", "Read Type": "Actual"},
    {"Account Number": "US02", "Meter Number": "MTR-1150", "Billing Start": "2026-02-01", "Billing End": "2026-02-28", "Usage": "121.4", "Unit": "MWh", "Tariff": "Industrial demand", "Read Type": "Estimated"},
]

TRAVEL_ROWS = [
    {"Report ID": "EXP-9912", "Expense ID": "AIR-1", "Expense Type": "Flight", "Start Date": "2026-02-03", "End Date": "2026-02-03", "Origin": "SFO", "Destination": "JFK", "Distance": "", "Distance Unit": "", "Amount": "812.40", "Currency": "USD"},
    {"Report ID": "EXP-9912", "Expense ID": "HTL-1", "Expense Type": "Hotel", "Start Date": "2026-02-03", "End Date": "2026-02-06", "Nights": "3", "Amount": "690", "Currency": "USD"},
    {"Report ID": "EXP-9918", "Expense ID": "GROUND-7", "Expense Type": "Ground transport", "Start Date": "2026-02-08", "Origin": "LHR", "Destination": "Office", "Distance": "", "Distance Unit": "", "Amount": "55", "Currency": "GBP"},
]


class Command(BaseCommand):
    help = "Seed a realistic demo tenant, sources, and ingestion records."

    def handle(self, *args, **options):
        org, _ = Organization.objects.get_or_create(name="Acme Industrials", slug="acme-industrials")
        Facility.objects.get_or_create(organization=org, code="DE01", defaults={"name": "Berlin Assembly Plant", "country": "DE", "grid_region": "DE"})
        Facility.objects.get_or_create(organization=org, code="US02", defaults={"name": "Ohio Distribution Hub", "country": "US", "grid_region": "RFCW"})

        sources = [
            (SourceSystem.SourceKind.SAP_ODATA, "sap-demo.csv", SAP_ROWS, normalize_sap_row),
            (SourceSystem.SourceKind.UTILITY_CSV, "green-button-demo.csv", UTILITY_ROWS, normalize_utility_row),
            (SourceSystem.SourceKind.CONCUR_EXPORT, "concur-itinerary-demo.csv", TRAVEL_ROWS, normalize_travel_row),
        ]
        for kind, filename, rows, normalizer in sources:
            source = self.get_source(org, kind)
            batch, _ = IngestionBatch.objects.get_or_create(
                organization=org,
                source_system=source,
                filename=filename,
                defaults={"notes": "Seeded demo batch for Railway/local review."},
            )
            save_records(batch, rows, normalizer)

        self.stdout.write(self.style.SUCCESS("Seeded demo data for acme-industrials."))

    def get_source(self, org, kind):
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
