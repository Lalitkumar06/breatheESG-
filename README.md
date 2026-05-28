# Breathe ESG — Carbon Accounting & Review Platform

A full-stack ESG data ingestion and analyst review platform. Ingests emissions data from SAP (Scope 1 & 3), utility providers (Scope 2), and corporate travel (Scope 3), normalizes and auto-flags anomalies, and provides an analyst review dashboard before records are locked for audit.

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 6 + Django REST Framework |
| Database | PostgreSQL (Railway) / SQLite (local dev) |
| Frontend | React 18 + Vite + Tailwind CSS v4 |
| Auth | DRF Token Authentication |
| Deployment | Railway (backend) + Vercel (frontend) |

---

## Quick Start (Local)

### Prerequisites
- Python 3.12+
- Node.js 18+
- Git

### 1. Clone the repo
```bash
git clone <your-repo-url>
cd breathe-esg
```

### 2. Backend setup
```bash
cd backend

# Create virtual environment on a drive with space
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install --no-cache-dir -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env — set SECRET_KEY and DATABASE_URL

# Run migrations
python manage.py migrate

# Seed sample data (2 tenants + 75 emission records)
python manage.py seed_data

# Start dev server
python manage.py runserver 8000
```

Backend will be available at: `http://localhost:8000`
Django Admin: `http://localhost:8000/admin/` (login: admin / admin123)

### 3. Frontend setup
```bash
cd ../frontend
npm install --legacy-peer-deps
npm run dev
```

Frontend will be available at: `http://localhost:5173`

---

## Default Credentials

| Username | Password | Role |
|----------|----------|------|
| `admin` | `admin123` | Superuser (all tenants) |
| `acme_analyst` | `analyst123` | ACME Corp analyst |
| `greentech_analyst` | `analyst123` | GreenTech Ltd analyst |

---

## Loading Sample Data

Sample data is loaded automatically by `seed_data`. To reload from scratch:

```bash
python manage.py flush --no-input
python manage.py seed_data
```

Sample files are in `backend/sample_data/`:
- `sap_sample.tsv` — 30 rows, SAP MM51 format, German headers
- `utility_sample.csv` — 20 rows, 3 meters across 2 sites
- `travel_sample.csv` — 25 rows, mixed AIR/HOTEL/CAR/RAIL

You can also upload them manually via the UI at `/upload`.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login/` | Get auth token |
| POST | `/api/auth/logout/` | Invalidate token |
| GET | `/api/auth/me/` | Current user info |
| POST | `/api/ingest/upload/` | Upload CSV/TSV file |
| GET | `/api/jobs/` | List ingestion jobs |
| GET | `/api/jobs/{id}/` | Job detail + row counts |
| GET | `/api/records/` | List records (filterable) |
| PATCH | `/api/records/{id}/` | Edit record |
| POST | `/api/records/{id}/approve/` | Approve record |
| POST | `/api/records/{id}/reject/` | Reject with reason |
| POST | `/api/records/{id}/flag/` | Flag as suspicious |
| POST | `/api/records/bulk-approve/` | Approve multiple |
| GET | `/api/records/{id}/history/` | Audit trail |
| GET | `/api/dashboard/summary/` | CO2e totals by scope |

---

## Project Structure

```
breathe-esg/
├── backend/
│   ├── breathe/           # Django settings + URLs
│   ├── core/              # Tenant, UserProfile, AuditLog
│   ├── ingestion/         # Jobs, parsers, pipeline, flagging
│   │   ├── parsers/       # sap_parser, utility_parser, travel_parser
│   │   ├── normalizers.py # Unit conversion (fuel/electricity/distance)
│   │   ├── emission_factors.py
│   │   ├── flagging.py    # Auto-flag logic (6 rules)
│   │   └── pipeline.py    # Background threading
│   ├── emissions/         # EmissionRecord model + review API
│   ├── dashboard/         # Summary aggregation API
│   ├── lookups/           # PlantLookup, EmissionFactor
│   ├── sample_data/       # 3 CSV/TSV sample files
│   ├── Procfile           # Railway deployment
│   ├── requirements.txt
│   └── runtime.txt
├── frontend/
│   ├── src/
│   │   ├── api/           # Axios client
│   │   ├── context/       # AuthContext
│   │   ├── components/    # Sidebar, StatusBadge
│   │   └── pages/         # Dashboard, Upload, ReviewQueue, RecordDetail, Jobs, Login
│   └── vercel.json
├── MODEL.md
├── DECISIONS.md
├── TRADEOFFS.md
├── SOURCES.md
└── README.md
```

---

## Auto-Flagging Rules

Records are automatically flagged (`status=FLAGGED`) if:

1. `activity_date` is in the future
2. `activity_date` is more than 2 years old
3. `co2e_kg` is 0 or NULL after processing
4. Unit was unrecognized and a fallback was used
5. `quantity_normalized` is negative
6. `quantity_normalized` > 3 standard deviations from mean for that category+tenant

---

## Deployment

### Backend (Railway)

1. Push `backend/` to a Git repo
2. Create a new Railway project → Deploy from GitHub
3. Add a PostgreSQL plugin
4. Set environment variables:
   - `SECRET_KEY` = random 50-char string
   - `DATABASE_URL` = automatically set by Railway PostgreSQL plugin
   - `DEBUG` = `False`
   - `ALLOWED_HOSTS` = `your-railway-domain.railway.app`
   - `CORS_ALLOWED_ORIGINS` = `https://your-vercel-app.vercel.app`
5. Railway runs `Procfile`: migrations → collectstatic → gunicorn
6. Run seed: `railway run python manage.py seed_data`

### Frontend (Vercel)

1. Push `frontend/` to a Git repo
2. Import into Vercel → Framework: Vite
3. Set env: `VITE_API_URL` = `https://your-railway-domain.railway.app`
4. Update `vite.config.ts` proxy target to production URL
5. Deploy — Vercel handles SPA routing via `vercel.json` rewrites

---

## Deployed URL

> **Backend API:** [To be filled after Railway deployment]
> **Frontend:** [To be filled after Vercel deployment]

---

## Notes

- Raw uploaded files are never deleted (preserved in `backend/media/raw_uploads/`)
- Locked records (`is_locked=True`) cannot be edited via API
- Background ingestion uses Python threading (TODO: migrate to Celery + Redis for production scale)
- Emission factors sourced from DEFRA 2023 and CEA India 2022-23
