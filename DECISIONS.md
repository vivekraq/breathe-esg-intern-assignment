# Decisions

## Source Subsets

SAP: I chose a CSV export shaped like SAP S/4HANA purchase order OData output, not IDoc. OData is easier for a prototype and realistic for enterprise integrations using `API_PURCHASEORDER_PROCESS_SRV`; the sample includes SAP-style German headers (`Einkaufsbeleg`, `Werk`, `Menge`, `MEINS`) because many SAP tenants are localized. I handle purchase order item rows for diesel and gasoline purchases plus unknown procurement items. I ignore multi-segment IDoc parsing, service entry sheets, goods receipt reconciliation, and tax/pricing conditions.

Utility: I chose Green Button-style utility portal CSV because facilities teams often download usage and billing data manually even when APIs exist. The model keeps billing start/end dates because billing periods do not align with calendar months. I handle kWh/MWh electricity usage, meter number, tariff, actual vs estimated read. I ignore PDF bill extraction, demand charge calculations, interval data, and supplier-specific tariff logic.

Travel: I chose a Concur-like itinerary/report export. The sample includes flights, hotel nights, and ground transport. Flights can be computed from distance if present, or inferred from airport code pairs when distance is absent. Hotels use nights. I ignore rail routing APIs, multi-leg itinerary expansion, cabin class multipliers, radiative forcing choices, and currency reconciliation.

## Ingestion Mechanism

All three sources use CSV upload in the prototype. That keeps the analyst workflow testable and fits the assignment timeline. The backend source abstractions still preserve where the data came from, so an API pull can later create the same `IngestionBatch` and `EmissionRecord` rows.

## Review Workflow

Rows start as `pending` unless normalization produces suspicion flags, in which case they start as `needs_fix`. Analysts can approve, reject, or lock. Locking is allowed only after approval because locked rows represent the audit-ready set.

## PM Questions I Would Ask

- Which clients and jurisdictions are in the first onboarding wave?
- Do analysts need row-level editing before approval, or only comments and rejection?
- Which emission factor library is authoritative for the product today?
- Should procurement spend be converted using spend-based factors, material-based factors, or excluded unless material/quantity is known?
- Is the audit lock reversible by an admin, or permanent?
- Should source connectors run on a schedule, on demand, or both?
- What identity provider and tenant access model should be used?
