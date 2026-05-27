# Breathe ESG Tech Intern Assignment

Prototype ingestion and analyst review app for SAP fuel/procurement data, utility electricity data, and corporate travel data.

## Stack

- Django + Django REST Framework backend
- React + Vite frontend
- SQLite locally, Postgres-ready via `DATABASE_URL`

## Local Run

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173
Backend API: http://localhost:8000/api/

Demo tenant header is set by the frontend as `X-Org-Slug: acme-industrials`.

## Railway Deployment

This project is configured to deploy as one Railway service. Django serves both `/api/` and the built React dashboard.

1. Push this folder to GitHub.
2. In Railway, create a new project from that GitHub repo.
3. Add a PostgreSQL database service.
4. In the Django service variables, set:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
SECRET_KEY=<any long random string>
DEBUG=False
ALLOWED_HOSTS=*
```

If your Railway PostgreSQL service is named `breathe-esg-db`, use:

```text
DATABASE_URL=${{breathe-esg-db.DATABASE_URL}}
```

Railway will use `railway.json` to build the React app, collect static files, run migrations, seed demo data, and start Gunicorn.

After deployment, generate a public domain in the service Networking tab. The same URL opens the dashboard and serves the API.
