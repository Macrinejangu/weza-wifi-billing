# weza-wifi-billing

Weza Wi-Fi Billing System. This repository contains two React apps, a shared FastAPI backend and a local PostgreSQL setup.

## Repository layout

| Path | What lives there |
| --- | --- |
| `apps/customer-portal/src/` | Customer portal pages, layouts, and Weza Assist |
| `apps/operator-dashboard/src/` | Administrator and operator pages and layouts |
| `apps/shared/` | Frontend code used by both portals |
| `backend/app/api/` | Customer, staff, and payment API routes |
| `backend/app/config.py` | Backend environment settings |
| `backend/app/db/` and `backend/app/models/` | PostgreSQL connections and data models |
| `backend/app/services/` | Business logic for purchases, payments, access, and router operations |
| `backend/migrations/` and `backend/tests/` | Database updates and backend tests |
| `backend/pyproject.toml` | Backend and test dependencies |
| `docs/` | API contracts, setup guides, and handover checks |
| `.env.example` and `compose.yaml` | Root environment template and local PostgreSQL setup |
| `package.json` and `package-lock.json` | Shared frontend scripts and dependencies |
| `.github/workflows/ci.yml` | Pull request checks |

## Batch 1 · Clone and install

Each developer follows these steps once the reviewed foundation reaches `main`. Install Git, Node 22.12+ (22.x) or Node 24, Python 3.12, and Docker with the Compose plugin.

```sh
git clone https://github.com/Macrinejangu/weza-wifi-billing.git
cd weza-wifi-billing
cp .env.example .env
npm ci
cd backend
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
cd ..
```

On Windows PowerShell, use `Copy-Item .env.example .env`, `py -3.12 -m venv .venv` and `.\.venv\Scripts\Activate.ps1` in place of the corresponding commands above.

## Batch 2 · Start locally

Start PostgreSQL from the repository root. Keep `.env` local to your machine.

```sh
docker compose up -d --wait db
cd backend
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

If you open a new terminal for the backend, activate its virtual environment again. Run each frontend in a separate terminal from the repository root.

| Command | Open |
| --- | --- |
| `npm run dev:customer` | [Customer portal](http://127.0.0.1:5173) |
| `npm run dev:operator` | [Operator dashboard](http://127.0.0.1:5174) |
| Backend command above | [Health](http://127.0.0.1:8000/health) and [OpenAPI docs](http://127.0.0.1:8000/docs) |

The API health endpoint returns `{"status":"ok"}`. See the [database guide](docs/database-decision.md) for the migration check and port configuration.

### Frontend demo mode

Both apps default to live data or an unavailable state. To use demo records, add
the following to `.env.development.local` inside the app you want to preview
(`apps/customer-portal` or `apps/operator-dashboard`), then restart Vite.

```dotenv
VITE_USE_DEMO_DATA=true
```

Open **Preview Dashboard (Development Only)** on the staff sign-in screen for
the operator preview. The customer portal shows demo records on the existing
routes. Demo changes and checkout are local previews. Production builds
disable demo mode even when the flag is set.

For the customer portal's live package catalogue, set
`VITE_API_BASE_URL=http://127.0.0.1:8000` in
`apps/customer-portal/.env.development.local` when running the backend locally.
When unset, the portal requests `/api/packages/` on the same origin. Set
`VITE_API_BASE_URL` at build time if the production API uses a different origin,
and add the frontend origin to the API's `CORS_ORIGINS`.

### Test a checkout and see the expiry

See the [pilot handover checklist](docs/pilot-handover.md) for a clean setup and acceptance steps.

Use a disposable database with one customer, one staff account and an active
hotspot package. Apply migrations before starting the API. For a simulated
checkout, set `ENABLE_MOCK_PAYMENTS=true` and `ROUTER_MODE=mock` on the backend.
Leave Daraja sandbox payments and direct device verification off. Run the
customer portal in development mode with `VITE_ENABLE_MOCK_CHECKOUT=true`,
`VITE_SANDBOX_PACKAGE_ID` set to the test package ID, and demo records off.
The paid screen identifies the simulated payment, and the connection screen
identifies simulated access.

In another terminal with the same database settings, run this from `backend/`:

```sh
python -m app.expire_sessions
```

Keep this process running throughout the test. In the portal, open the package,
sign in, simulate payment and open the connection status. In the staff dashboard,
find the matching payment and session. Wait for the package to end and refresh
Sessions to check its expired status. No money or router is involved in this mode.

For a separately configured lab with Daraja sandbox and MikroTik, turn mock
payments off. Enable `ENABLE_DARAJA_SANDBOX_PAYMENTS` and
`ENABLE_DIRECT_HOTSPOT_CHECKOUT`, and set `ROUTER_MODE=mikrotik`. The
customer build uses `VITE_ENABLE_SANDBOX_CHECKOUT=true`,
`VITE_REQUIRE_HOTSPOT_DEVICE=true` and the test package ID. The customer API
needs a direct connection from the hotspot device. Start Uvicorn with
`--no-proxy-headers` and use a separate HTTPS ingress for Daraja's callback.
Keep the expiry process on while access is enabled. The Daraja integration
supports sandbox only.

## Batch 3 · Run checks and start your Jira task

```sh
npm test
npm run build
cd backend
python -m pytest
```

The PostgreSQL test skips unless you set `TEST_DATABASE_URL`. Pull request checks start a fresh database and run the test. See the [database guide](docs/database-decision.md) for local instructions.

Follow the [branch and pull request workflow](docs/contributing.md) using your existing Jira sprint and issue.

## Optional router connectivity check

The `/router/status` endpoint checks whether the backend reaches the
configured MikroTik router and reads its identity.

Add the following settings to your existing local `.env`. Refer to
`.env.example` for the variable names.

- `WEZA_API_KEY`: a private key callers supply to the status endpoint.
- `ROUTER_HOST`: the test router's hostname or IP address.
- `ROUTER_USERNAME`: the router account username.
- `ROUTER_PASSWORD`: the router account password.
- `ROUTER_PORT`: defaults to `8728`.
- `ROUTER_TIMEOUT`: connection timeout in seconds, defaults to `5`.

- `EXPECTED_ROUTER_IDENTITY`: the router name expected in the response.
- `ROUTER_USE_SSL`: `false` for the isolated lab, `true` for API-SSL.
- `ROUTER_TLS_CA_FILE`: path to a trusted CA certificate file, when needed.
- `ROUTER_TLS_SERVER_NAME`: certificate hostname, defaults to `ROUTER_HOST`.

For API-SSL, set `ROUTER_USE_SSL=true` and `ROUTER_PORT=8729`.

Keep real credentials in your local `.env`.

The default lab configuration uses the plain RouterOS API.
Certificate-verified API-SSL is supported. A live certificate-verified
connection still needs testing before deployment.

With the backend running, open its `/docs` page, expand
`GET /router/status`, select “Try it out”, and enter your `WEZA_API_KEY`
in the `x-weza-api-key` field.

Expected responses:

- `200`: the router identity request succeeded.
- `401`: the supplied API key is missing or incorrect.
- `502`: the router returned a missing, invalid, or unexpected identity.
- `503`: API authentication or router identity verification is unconfigured,
  or the router connection failed.

Run the router endpoint tests from the repository root with the backend
virtual environment activated:

```sh
cd backend
python -m pytest tests/test_router.py -q
```

These tests use simulated router responses and require no live router.

See the [router connectivity guide](docs/router-connectivity.md) for
security settings and recorded lab test results.
