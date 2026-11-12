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
