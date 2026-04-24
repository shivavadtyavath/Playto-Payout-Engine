# Playto Payout Engine

A production-grade payout engine for Indian agencies and freelancers. Merchants accumulate balance from international customer payments and withdraw to their Indian bank accounts.

**Stack:** Django + DRF · PostgreSQL · Celery + Redis · React + Tailwind CSS

**GitHub:** https://github.com/shivavadtyavath/Playto-Payout-Engine

---

## Live Deployment

### Backend → Railway (free)

1. Push this repo to GitHub: `https://github.com/shivavadtyavath/Playto-Payout-Engine`
2. Go to [railway.app](https://railway.app) → Login with GitHub → **New Project** → **Deploy from GitHub repo**
3. Select the repo → set **Root Directory** to `backend`
4. Add **PostgreSQL**: click `+ New` → `Database` → `Add PostgreSQL` (Railway auto-sets `DATABASE_URL`)
5. Add **Redis**: click `+ New` → `Database` → `Add Redis` (Railway auto-sets `REDIS_URL`)
6. In the backend service → **Variables** tab, add:
   ```
   DJANGO_SECRET_KEY   = any-50-char-random-string
   DEBUG               = False
   CORS_ALLOWED_ORIGINS = https://YOUR-APP.vercel.app
   ```
7. Railway auto-deploys. Copy the backend URL (e.g. `https://playto-backend.up.railway.app`)

**Add Celery worker service:**
- In Railway project → `+ New` → `GitHub Repo` → same repo → Root: `backend`
- Override start command: `celery -A playto worker --loglevel=info --concurrency=2`
- Add same env vars as backend service

**Add Celery beat service:**
- Same as worker but start command: `celery -A playto beat --loglevel=info`

---

### Frontend → Vercel

1. Go to [vercel.com](https://vercel.com) → **New Project** → Import from GitHub
2. Select `Playto-Payout-Engine` repo
3. Set **Root Directory** to `frontend`
4. Add environment variable:
   ```
   REACT_APP_API_URL = https://YOUR-RAILWAY-BACKEND-URL.up.railway.app/api/v1
   ```
5. Click **Deploy** → done in ~2 minutes

Your live URLs will be:
- Frontend: `https://playto-payout-engine.vercel.app`
- Backend API: `https://playto-backend.up.railway.app`

---

## Quick Start (Docker)

```bash
# Clone and start everything
git clone <repo-url>
cd playto-payout-engine

docker-compose up --build
```

This starts:
- PostgreSQL on port 5432
- Redis on port 6379
- Django API on http://localhost:8000
- Celery worker (processes payouts)
- Celery beat (scheduler: every 10s for pending, every 30s for stuck)
- React dashboard on http://localhost:3000

The backend container automatically runs migrations and seeds 3 test merchants on startup.

---

## Manual Setup

### Prerequisites

- Python 3.11+
- Node.js 20+
- PostgreSQL 15+
- Redis 7+

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL and REDIS_URL

# Run migrations
python manage.py migrate

# Seed test data (3 merchants with bank accounts and credit history)
python manage.py seed_data

# Start API server
python manage.py runserver 0.0.0.0:8000

# In a separate terminal: start Celery worker
celery -A playto worker --loglevel=info

# In a separate terminal: start Celery beat (scheduler)
celery -A playto beat --loglevel=info
```

### Frontend

```bash
cd frontend

npm install
npm start
# Opens http://localhost:3000
```

---

## Test Merchants

After running `seed_data`, three merchants are available:

| Merchant | ID | Balance |
|---|---|---|
| Arjun Sharma Design Studio | `11111111-1111-1111-1111-111111111111` | ₹10,500 |
| Priya Nair Freelance Dev | `22222222-2222-2222-2222-222222222222` | ₹11,700 |
| Rahul Mehta Content Agency | `33333333-3333-3333-3333-333333333333` | ₹9,300 |

Switch between merchants using the dropdown in the dashboard header.

---

## API Reference

All endpoints require `X-Merchant-ID` header.

### Get Balance
```
GET /api/v1/merchants/me/
X-Merchant-ID: <merchant-uuid>
```

### Get Ledger
```
GET /api/v1/merchants/me/ledger/
X-Merchant-ID: <merchant-uuid>
```

### Get Bank Accounts
```
GET /api/v1/merchants/me/bank-accounts/
X-Merchant-ID: <merchant-uuid>
```

### Create Payout
```
POST /api/v1/payouts/
X-Merchant-ID: <merchant-uuid>
Idempotency-Key: <uuid>
Content-Type: application/json

{
  "amount_paise": 50000,
  "bank_account_id": "<bank-account-uuid>"
}
```

### List Payouts
```
GET /api/v1/payouts/
X-Merchant-ID: <merchant-uuid>
```

---

## Running Tests

```bash
cd backend

# Run all tests
pytest

# Run specific test files
pytest tests/test_concurrency.py -v
pytest tests/test_idempotency.py -v
pytest tests/test_state_machine.py -v
pytest tests/test_payout_api.py -v
pytest tests/test_celery_tasks.py -v
pytest tests/test_models.py -v
```

The concurrency test uses `TransactionTestCase` with real threads. It requires a live PostgreSQL connection (not SQLite) to test `SELECT FOR UPDATE` semantics correctly.

---

## Project Structure

```
playto-payout-engine/
├── backend/
│   ├── playto/          # Django project (settings, celery, urls)
│   ├── merchants/       # Merchant, BankAccount models + auth
│   ├── ledger/          # LedgerEntry model + balance queries
│   ├── payouts/         # Payout model, state machine, views, tasks
│   ├── idempotency/     # IdempotencyKey model + decorator
│   └── tests/           # All tests
├── frontend/
│   └── src/
│       ├── components/  # BalanceCard, PayoutForm, PayoutHistory, LedgerTable
│       ├── context/     # MerchantContext + QueryClient
│       ├── api/         # API client
│       └── utils/       # formatters (paise → INR)
├── docker-compose.yml
├── README.md
└── EXPLAINER.md
```
