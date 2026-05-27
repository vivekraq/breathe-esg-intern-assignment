# Data Model

The prototype is built around tenant-scoped ingestion batches and immutable-ish normalized emission rows. The important choice is to keep the source payload beside the normalized fields rather than overwriting messy input too early.

## Entities

`Organization` is the tenant boundary. Every facility, source, batch, record, and audit event belongs to an organization. In production this would be enforced from the authenticated user; in the prototype it is selected with `X-Org-Slug`.

`Facility` maps client-specific operational codes to a usable location. SAP plant codes and utility account numbers are treated as external identifiers, because real clients often have terse codes that need a lookup table before analysts can understand them.

`SourceSystem` identifies the source of truth for a row: SAP OData purchase order export, utility portal CSV, or Concur itinerary export. It stores a kind, display name, external reference, and source metadata.

`IngestionBatch` captures one import event: source, filename, row counts, failures, received time, and processed time. This lets analysts and auditors ask what arrived together.

`EmissionRecord` is the normalized review unit. It stores:

- Tenant and source tracking: `organization`, `source_system`, `batch`, `external_id`, `source_hash`, `source_row_number`, and `source_payload`.
- Carbon classification: `scope`, `category`, `activity_type`, and `emission_factor_ref`.
- Time fields: `activity_date`, `period_start`, and `period_end`, because utility bills and travel periods do not always match a single day.
- Unit normalization: original `quantity` and `unit`, plus `normalized_quantity` and `normalized_unit`.
- Review state: `pending`, `needs_fix`, `approved`, `rejected`, or `locked`.
- Analyst safety signals: `suspicious_flags` and `error_message`.
- Audit lock fields: `approved_by`, `approved_at`, `locked_at`.
- `edits`, used to preserve analyst overrides separately from the source payload.

`AuditEvent` records actor, action, before, after, and timestamp for review changes. The app prevents edits after a record is locked.

## Why This Shape

Multi-tenancy is explicit on every table that contains client data. This makes query filtering boring and reliable, and it avoids depending on joins to infer tenant ownership.

Source-of-truth tracking uses both `source_system` and `source_hash`. The hash deduplicates repeat imports of the same row without pretending the source ID alone is always globally unique. The full `source_payload` is retained so an auditor can see exactly what the client supplied.

Unit normalization is stored, not computed only at render time, because analysts need to review the actual transformed values before approval. Original units stay visible so bad conversions can be challenged.

Auditability is split between current record state and `AuditEvent`. The current row answers operational questions quickly; events answer who changed what and when.

Scope/category categorization is deliberately simple:

- SAP fuel purchase rows map to Scope 1 stationary combustion.
- Utility electricity rows map to Scope 2 purchased electricity.
- Travel rows map to Scope 3 business travel.
- Non-fuel SAP procurement rows map to Scope 3 purchased goods and are flagged if the factor cannot be mapped.

In a production system, emission factor versions would be normalized into their own table. Here, `emission_factor_ref` is a string because the assignment is about ingestion and review flow rather than factor library governance.
