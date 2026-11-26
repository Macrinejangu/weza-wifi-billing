# Local database and migrations

Use PostgreSQL 18 for local development. Compose binds it to the loopback interface and stores data in a named volume. If port 5432 is busy, change both `POSTGRES_PORT` and the port in `DATABASE_URL` in your root `.env`. Developers with an existing local PostgreSQL installation can instead create a dedicated database and set `DATABASE_URL` to its connection string.

SQLAlchemy provides Python database access, psycopg is the PostgreSQL driver, and Alembic records schema changes. The maintainer [ended Prisma Client Python development](https://github.com/RobertCraigie/prisma-client-py/issues/1073) and archived the repository. The migration setup uses Alembic with the same database URL for online and offline commands.

From `backend/`, with the virtual environment active and the local database running:

```sh
python -m alembic upgrade head
python -m alembic current
```

Run `python -m alembic heads` to see the current schema revision. Before testing, confirm `python -m alembic current` reports that revision.

For a schema change, run `python -m alembic revision -m "describe the change"` and fill in the generated upgrade and downgrade functions. Test the migration against a disposable local database. Keep one migration head. When two schema branches overlap, coordinate their revision order during review. Include the migration in the same pull request as its model changes.

Run `docker compose down` from the root to stop PostgreSQL and retain local data. Remove its volume only when you intend to erase the local database. The sample values in `.env.example` are for local development. Keep private values in your environment.

## Run the database test

The test checks the migration revision and writes only to a temporary table. Run it against a separate test database, never against the development database in `DATABASE_URL`.

Create the test database once from the repo root. Replace `weza` with your `POSTGRES_USER` if you changed it:

```sh
docker compose exec db psql -U weza -d weza -c "CREATE DATABASE weza_test"
```

Then migrate it and run the test. Replace the password and port with your own values from `.env` if they differ from the sample:

```sh
export TEST_DATABASE_URL="postgresql+psycopg://weza:weza_local_only@127.0.0.1:5432/weza_test"
cd backend
DATABASE_URL="$TEST_DATABASE_URL" python -m alembic upgrade head
python -m pytest tests/test_db.py
```
