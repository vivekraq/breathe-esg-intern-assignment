# Breathe ESG Ingestion Review Prototype

A Django REST + React prototype for ingesting enterprise activity data, normalizing it into emission review rows, and allowing an analyst to approve or lock rows before audit.

The prototype handles three realistic source shapes:

- SAP fuel/procurement rows from an OData-style purchase order export
- Utility electricity rows from a Green Button / utility portal CSV export
- Corporate travel rows from a Concur-style itinerary or expense export

The main product flow is: import source rows, normalize quantities and units, flag suspicious records, review records in a dashboard, approve rows, and lock approved rows for audit.

## Repository Structure

```text
.
├── breathe/                 # Django project settings, URL routing, WSGI entrypoint
├── ingest/                  # Django app: models, API views, serializers, normalizers
├── frontend/                # React + Vite analyst dashboard
├── samples/                 # Sample CSV files for the three supported source types
├── MODEL.md                 # Data model explanation and reasoning
├── DECISIONS.md             # Ambiguities, source choices, PM questions
├── TRADEOFFS.md             # Deliberately omitted work
├── SOURCES.md               # Source research and sample-data rationale
├── railway.json             # Railway build/deploy configuration
├── render.yaml              # Optional Render deployment scaffold
└── requirements.txt         # Python dependencies
```

## Tech Stack

- Backend: Django 5, Django REST Framework
- Frontend: React 18, Vite, lucide-react
- Local database: SQLite
- Production database: PostgreSQL through `DATABASE_URL`
- Static serving: WhiteNoise
- Deployment target: Railway

## Local Development

Run these commands from the project root.

### 1. Backend

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Backend API:

```text
http://127.0.0.1:8000/api/
```

Health check:

```text
http://127.0.0.1:8000/api/health/
```

### 2. Frontend

Open a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend:

```text
http://127.0.0.1:5173
```

The frontend sends this tenant header on API requests:

```text
X-Org-Slug: acme-industrials
```

## Demo Data

Seed demo data with:

```powershell
python manage.py seed_demo
```

The command creates:

- One tenant: `acme-industrials`
- Two facilities
- Three source systems
- SAP, utility, and travel ingestion batches
- Normalized emission records with a mix of clean and suspicious rows

Sample upload files are available in:

```text
samples/sap_fuel_procurement.csv
samples/utility_electricity.csv
samples/concur_travel.csv
```

## Core Data Model

The review unit is `EmissionRecord`.

Important fields include:

- `organization`: tenant boundary
- `source_system`: SAP, utility CSV, or Concur export
- `batch`: import event that produced the row
- `external_id`: source-facing row identifier
- `source_hash`: deduplication key for repeat imports
- `source_payload`: original source row as JSON
- `quantity` / `unit`: raw source values
- `normalized_quantity` / `normalized_unit`: normalized values used for review
- `scope` and `category`: Scope 1, 2, or 3 classification
- `co2e_kg`: computed prototype emissions
- `suspicious_flags`: analyst review signals
- `review_status`: `pending`, `needs_fix`, `approved`, `rejected`, or `locked`

Review actions create `AuditEvent` rows with actor, action, before/after payloads, and timestamp.

See `MODEL.md` for the full explanation.

## API Overview

Base path:

```text
/api/
```

Endpoints:

```text
GET  /api/health/
GET  /api/dashboard/
GET  /api/sources/
GET  /api/batches/
GET  /api/records/
POST /api/ingest/sap/
POST /api/ingest/utility/
POST /api/ingest/travel/
POST /api/records/<id>/review/
GET  /api/records/<id>/audit/
```

CSV upload endpoints expect multipart form data with the file field named:

```text
file
```

Review actions accept:

```json
{
  "action": "approve",
  "actor": "analyst@breatheesg.com"
}
```

Supported actions:

```text
approve
reject
lock
edit
```

Only approved records can be locked.

## Source Handling

### SAP

Chosen shape: SAP S/4HANA purchase order OData-style export.

Handled:

- German and English-ish headers
- plant code lookup
- date parsing across common formats
- litre and gallon fuel quantities
- diesel and gasoline mapping to Scope 1 stationary combustion
- unknown procurement rows flagged for review

Ignored:

- IDoc segment parsing
- goods receipt reconciliation
- service entry sheets
- pricing/tax condition logic

### Utility Electricity

Chosen shape: utility portal / Green Button-style CSV.

Handled:

- account and meter identifiers
- billing/service start and end dates
- kWh and MWh normalization
- tariff and read type
- estimated-read flagging
- non-calendar billing periods

Ignored:

- PDF bill extraction
- interval data
- demand charges
- market-based Scope 2 contracts

### Corporate Travel

Chosen shape: Concur-style itinerary or expense export.

Handled:

- flights, hotels, and ground transport
- airport-code distance inference for selected routes
- hotel nights
- missing-distance flags
- Scope 3 business travel categorization

Ignored:

- cabin class multipliers
- full airport distance database
- multi-leg itinerary expansion
- vehicle type detection

See `SOURCES.md` and `DECISIONS.md` for research notes and rationale.

## Railway Deployment

This project is configured as one Railway app service. Django serves both:

- React dashboard at `/`
- API at `/api/`

### 1. Create Railway Services

In Railway:

1. Create a new project from the GitHub repository.
2. Add a PostgreSQL database service.
3. Open the app service, not the database service.
4. Add the environment variables below.

### 2. Required Variables

If your PostgreSQL service is named `breathe-esg-db`, set:

```text
DATABASE_URL=${{breathe-esg-db.DATABASE_URL}}
SECRET_KEY=<long random secret>
DEBUG=False
ALLOWED_HOSTS=*
```

Use Railway's reference variable picker when possible:

```text
breathe-esg-db -> DATABASE_URL
```

Add `DATABASE_URL` to the app service. Do not add it only to the database service.

### 3. Deploy

Railway reads `railway.json` and runs:

```text
pip install -r requirements.txt
cd frontend && npm ci && npm run build
python manage.py collectstatic --noinput
python manage.py migrate
python manage.py seed_demo
gunicorn breathe.wsgi:application --bind 0.0.0.0:$PORT
```

After deployment, open the app service Settings and use the public domain shown under Public Networking.

Example:

```text
https://breathe-esg-api-production-xxxx.up.railway.app
```

Health check:

```text
https://breathe-esg-api-production-xxxx.up.railway.app/api/health/
```

Expected response:

```json
{"ok": true}
```

## Railway Troubleshooting

### Database page says "You have no tables"

The app did not run migrations against Railway Postgres.

Check that `DATABASE_URL` exists on the app service and references the database service:

```text
${{breathe-esg-db.DATABASE_URL}}
```

Then redeploy the app service.

### `DATABASES is improperly configured`

`DATABASE_URL` is empty or unresolved.

Fix the app service variable using Railway's reference picker.

### App is online but dashboard does not load records

Check:

```text
/api/health/
/api/dashboard/
```

If health works but dashboard has no rows, run or re-run the app deployment so `python manage.py seed_demo` executes.

### Static files are missing

Redeploy the app service. The build command must complete the frontend build and `collectstatic`.

## Reviewer Notes

This is intentionally a focused prototype. The emphasis is on data-model clarity, realistic ingestion assumptions, normalization, analyst review, and auditability.

The main design documents are:

- `MODEL.md`
- `DECISIONS.md`
- `TRADEOFFS.md`
- `SOURCES.md`
