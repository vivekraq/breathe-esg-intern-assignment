import csv
import hashlib
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import TextIOWrapper

from django.utils import timezone

from .models import EmissionRecord, Facility, IngestionBatch


PLANT_ALIASES = {
    "Werk": "plant_code",
    "Plant": "plant_code",
    "werks": "plant_code",
    "Belegdatum": "document_date",
    "Document Date": "document_date",
    "Menge": "quantity",
    "Quantity": "quantity",
    "MEINS": "unit",
    "Unit": "unit",
    "Material": "material",
    "Material Description": "material_description",
    "Einkaufsbeleg": "purchase_order",
    "Purchase Order": "purchase_order",
    "Item": "item",
}

UTILITY_ALIASES = {
    "Account Number": "account_number",
    "Meter Number": "meter_number",
    "Service Start": "period_start",
    "Service End": "period_end",
    "Billing Start": "period_start",
    "Billing End": "period_end",
    "Usage": "usage",
    "Usage (kWh)": "usage",
    "Unit": "unit",
    "Tariff": "tariff",
    "Read Type": "read_type",
}

TRAVEL_ALIASES = {
    "Report ID": "report_id",
    "Expense ID": "expense_id",
    "Type": "type",
    "Expense Type": "type",
    "Start Date": "start_date",
    "End Date": "end_date",
    "Origin": "origin",
    "Destination": "destination",
    "Distance": "distance",
    "Distance Unit": "distance_unit",
    "Nights": "nights",
    "Amount": "amount",
    "Currency": "currency",
}

UNIT_TO_BASE = {
    "l": ("litre", Decimal("1")),
    "liter": ("litre", Decimal("1")),
    "litre": ("litre", Decimal("1")),
    "gal": ("litre", Decimal("3.78541")),
    "gallon": ("litre", Decimal("3.78541")),
    "kwh": ("kWh", Decimal("1")),
    "mwh": ("kWh", Decimal("1000")),
    "km": ("km", Decimal("1")),
    "mi": ("km", Decimal("1.60934")),
    "mile": ("km", Decimal("1.60934")),
}

EMISSION_FACTORS = {
    "diesel_litre": Decimal("2.68"),
    "gasoline_litre": Decimal("2.31"),
    "electricity_kwh": Decimal("0.386"),
    "flight_km": Decimal("0.158"),
    "hotel_night": Decimal("15.00"),
    "rail_km": Decimal("0.041"),
    "car_km": Decimal("0.171"),
}

AIRPORT_DISTANCE_KM = {
    ("SFO", "JFK"): Decimal("4160"),
    ("JFK", "LHR"): Decimal("5540"),
    ("BLR", "DEL"): Decimal("1700"),
    ("DEL", "BOM"): Decimal("1140"),
}


def parse_csv_upload(upload):
    upload.seek(0)
    wrapper = TextIOWrapper(upload.file, encoding="utf-8-sig", newline="")
    reader = csv.DictReader(wrapper)
    return list(reader)


def normalize_headers(row, aliases):
    normalized = {}
    for key, value in row.items():
        normalized_key = aliases.get((key or "").strip(), (key or "").strip().lower().replace(" ", "_"))
        normalized[normalized_key] = (value or "").strip()
    return normalized


def row_hash(row):
    parts = [f"{key}={row.get(key, '')}" for key in sorted(row.keys())]
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def parse_decimal(value):
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, AttributeError):
        return None


def parse_date(value):
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def normalize_unit(quantity, unit):
    if quantity is None:
        return None, unit or "", None
    base_unit, multiplier = UNIT_TO_BASE.get((unit or "").lower(), (unit or "", Decimal("1")))
    return quantity * multiplier, base_unit, multiplier


def suspicious(*flags):
    return [flag for flag in flags if flag]


def find_facility(org, code):
    if not code:
        return None
    return Facility.objects.filter(organization=org, code__iexact=code).first()


def save_records(batch, rows, normalizer):
    created = 0
    failed = 0
    for index, raw in enumerate(rows, start=1):
        payload = normalizer(raw, batch.organization, index)
        payload["batch"] = batch
        payload["organization"] = batch.organization
        payload["source_system"] = batch.source_system
        try:
            _, was_created = EmissionRecord.objects.update_or_create(
                organization=batch.organization,
                source_system=batch.source_system,
                source_hash=payload["source_hash"],
                defaults=payload,
            )
            created += int(was_created)
            if payload.get("error_message"):
                failed += 1
        except Exception:
            failed += 1
    batch.row_count = len(rows)
    batch.failed_count = failed
    batch.status = IngestionBatch.Status.PROCESSED
    batch.processed_at = timezone.now()
    batch.save(update_fields=["row_count", "failed_count", "status", "processed_at"])
    return created, failed


def normalize_sap_row(raw, org, index):
    row = normalize_headers(raw, PLANT_ALIASES)
    quantity = parse_decimal(row.get("quantity"))
    unit = row.get("unit", "")
    normalized_quantity, normalized_unit, _ = normalize_unit(quantity, unit)
    material = (row.get("material_description") or row.get("material") or "").lower()
    activity_type = "diesel" if "diesel" in material else "gasoline" if "gas" in material else "purchased goods"
    scope = EmissionRecord.Scope.SCOPE_1 if activity_type in {"diesel", "gasoline"} else EmissionRecord.Scope.SCOPE_3
    category = (
        EmissionRecord.Category.STATIONARY_COMBUSTION
        if scope == EmissionRecord.Scope.SCOPE_1
        else EmissionRecord.Category.PURCHASED_GOODS
    )
    factor_key = f"{activity_type}_litre"
    co2e = normalized_quantity * EMISSION_FACTORS[factor_key] if factor_key in EMISSION_FACTORS and normalized_quantity else None
    external_id = f"{row.get('purchase_order', 'PO')}-{row.get('item', index)}"
    date = parse_date(row.get("document_date"))
    flags = suspicious(
        "unmapped_plant" if not find_facility(org, row.get("plant_code")) else "",
        "unknown_unit" if unit and normalized_unit == unit and unit.lower() not in UNIT_TO_BASE else "",
        "missing_date" if not date else "",
        "unmapped_material_factor" if co2e is None else "",
    )
    return {
        "external_id": external_id,
        "source_hash": row_hash(row),
        "source_row_number": index,
        "source_payload": row,
        "facility": find_facility(org, row.get("plant_code")),
        "activity_date": date,
        "period_start": date,
        "period_end": date,
        "scope": scope,
        "category": category,
        "activity_type": activity_type,
        "quantity": quantity,
        "unit": unit,
        "normalized_quantity": normalized_quantity,
        "normalized_unit": normalized_unit,
        "co2e_kg": co2e,
        "emission_factor_ref": "prototype factors: fuel litre defaults",
        "review_status": EmissionRecord.ReviewStatus.NEEDS_FIX if flags else EmissionRecord.ReviewStatus.PENDING,
        "suspicious_flags": flags,
        "error_message": "" if co2e is not None else "Could not map material/unit to an emission factor.",
    }


def normalize_utility_row(raw, org, index):
    row = normalize_headers(raw, UTILITY_ALIASES)
    quantity = parse_decimal(row.get("usage"))
    normalized_quantity, normalized_unit, _ = normalize_unit(quantity, row.get("unit") or "kWh")
    start = parse_date(row.get("period_start"))
    end = parse_date(row.get("period_end"))
    co2e = normalized_quantity * EMISSION_FACTORS["electricity_kwh"] if normalized_quantity else None
    meter = row.get("meter_number") or f"row-{index}"
    flags = suspicious(
        "billing_period_not_calendar_month" if start and end and (start.day != 1 or end.day not in (28, 29, 30, 31)) else "",
        "estimated_read" if "est" in (row.get("read_type") or "").lower() else "",
        "missing_meter" if not row.get("meter_number") else "",
        "unknown_unit" if row.get("unit") and normalized_unit == row.get("unit") and row.get("unit", "").lower() not in UNIT_TO_BASE else "",
    )
    return {
        "external_id": f"{meter}-{start or index}-{end or index}",
        "source_hash": row_hash(row),
        "source_row_number": index,
        "source_payload": row,
        "facility": Facility.objects.filter(organization=org, code__iexact=row.get("account_number", "")).first(),
        "activity_date": end,
        "period_start": start,
        "period_end": end,
        "scope": EmissionRecord.Scope.SCOPE_2,
        "category": EmissionRecord.Category.PURCHASED_ELECTRICITY,
        "activity_type": "electricity",
        "quantity": quantity,
        "unit": row.get("unit") or "kWh",
        "normalized_quantity": normalized_quantity,
        "normalized_unit": normalized_unit,
        "co2e_kg": co2e,
        "emission_factor_ref": "prototype US grid average electricity factor",
        "review_status": EmissionRecord.ReviewStatus.NEEDS_FIX if flags else EmissionRecord.ReviewStatus.PENDING,
        "suspicious_flags": flags,
        "error_message": "" if co2e is not None else "Could not normalize electricity usage.",
    }


def normalize_travel_row(raw, org, index):
    row = normalize_headers(raw, TRAVEL_ALIASES)
    travel_type = (row.get("type") or "").lower()
    start = parse_date(row.get("start_date"))
    end = parse_date(row.get("end_date")) or start
    distance = parse_decimal(row.get("distance"))
    distance_unit = row.get("distance_unit") or "km"
    if distance is None and row.get("origin") and row.get("destination"):
        pair = (row.get("origin", "").upper(), row.get("destination", "").upper())
        distance = AIRPORT_DISTANCE_KM.get(pair) or AIRPORT_DISTANCE_KM.get((pair[1], pair[0]))
        distance_unit = "km"
    normalized_quantity, normalized_unit, _ = normalize_unit(distance, distance_unit)
    nights = parse_decimal(row.get("nights"))
    if "hotel" in travel_type:
        normalized_quantity = nights
        normalized_unit = "night"
        factor_key = "hotel_night"
    elif "rail" in travel_type:
        factor_key = "rail_km"
    elif "car" in travel_type or "ground" in travel_type or "taxi" in travel_type:
        factor_key = "car_km"
    else:
        factor_key = "flight_km"
    co2e = normalized_quantity * EMISSION_FACTORS[factor_key] if normalized_quantity else None
    external_id = row.get("expense_id") or f"{row.get('report_id', 'TRIP')}-{index}"
    flags = suspicious(
        "distance_inferred_from_airport_codes" if not raw.get("Distance") and normalized_quantity and "hotel" not in travel_type else "",
        "missing_distance" if co2e is None and "hotel" not in travel_type else "",
        "missing_nights" if "hotel" in travel_type and not nights else "",
        "missing_date" if not start else "",
    )
    return {
        "external_id": external_id,
        "source_hash": row_hash(row),
        "source_row_number": index,
        "source_payload": row,
        "facility": None,
        "activity_date": end,
        "period_start": start,
        "period_end": end,
        "scope": EmissionRecord.Scope.SCOPE_3,
        "category": EmissionRecord.Category.BUSINESS_TRAVEL,
        "activity_type": travel_type or "travel",
        "quantity": distance or nights,
        "unit": distance_unit if "hotel" not in travel_type else "night",
        "normalized_quantity": normalized_quantity,
        "normalized_unit": normalized_unit,
        "co2e_kg": co2e,
        "emission_factor_ref": f"prototype travel factor: {factor_key}",
        "review_status": EmissionRecord.ReviewStatus.NEEDS_FIX if flags else EmissionRecord.ReviewStatus.PENDING,
        "suspicious_flags": flags,
        "error_message": "" if co2e is not None else "Could not compute travel emissions.",
    }
