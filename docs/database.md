# Local database and migrations

Use PostgreSQL 18 for local development. Compose binds it to the loopback interface and stores data in a named volume. If port 5432 is busy, change both `POSTGRES_PORT` and the port in `DATABASE_URL` in your root `.env`. Developers with an existing local PostgreSQL installation can instead create a dedicated database and set `DATABASE_URL` to its connection string.

SQLAlchemy provides Python database access, psycopg is the PostgreSQL driver, and Alembic records schema changes. The maintainer [ended Prisma Client Python development](https://github.com/RobertCraigie/prisma-client-py/issues/1073) and archived the repository. The migration setup uses Alembic with the same database URL for online and offline commands.

From `backend/`, with the virtual environment active and the local database running:

```sh
python -m alembic upgrade head
python -m alembic current
```

The starting revision is `0001 (head)`. It establishes migration tracking. Define packages, payments, sessions and staff user tables under WEZA-33 after reviewing the data model.

For a schema change, run `python -m alembic revision -m "describe the change"` and fill in the generated upgrade and downgrade functions. Test the migration against a disposable local database. Keep one migration head. When two schema branches overlap, coordinate their revision order during review. Include the migration in the same pull request as its model changes.

Run `docker compose down` from the root to stop PostgreSQL and retain local data. Remove its volume only when you intend to erase the local database. The sample values in `.env.example` are for local development. Keep private values in your environment.
