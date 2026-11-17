# weza-wifi-billing

Weza Wi-Fi Billing System. This repository contains two React apps, a shared FastAPI backend and a local PostgreSQL setup.

## Repository layout

```text
apps/
  customer-portal/        Customer-facing React/Vite app
  operator-dashboard/     Staff React/Vite app
backend/
  app/
    api/                  HTTP routes
    config.py             Environment and configuration
    db/                   PostgreSQL connection
  migrations/             Alembic revisions
  tests/                  FastAPI tests
  pyproject.toml          Backend and test dependencies
docs/
  database-decision.md             PostgreSQL and migration workflow
  api-contract.md        Current API contract
  contributing.md        Jira branches and pull requests
.env.example              Local environment template
compose.yaml              Local PostgreSQL service
.github/workflows/ci.yml  Pull request checks
package.json              Frontend workspace scripts
package-lock.json         Shared frontend dependency lockfile
```

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

Expect one starter heading per app and `{"status":"ok"}` from the API. The apps and API liveness check also run without PostgreSQL. See the [database guide](docs/database-decision.md) for the migration check and port configuration.

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

The current connection uses the plain RouterOS API. Confirm the lab's
network protection with the router owner. Deployment requires an agreed
secure connection setup.

With the backend running, open its `/docs` page, expand
`GET /router/status`, select “Try it out”, and enter your `WEZA_API_KEY`
in the `x-weza-api-key` field.

Expected responses:

- `200`: the router identity request succeeded.
- `401`: the supplied API key is missing or incorrect.
- `- `502`: the router returned a missing, invalid, or unexpected identity.
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