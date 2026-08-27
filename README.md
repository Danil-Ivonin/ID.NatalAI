# NatalAI persistence

The project currently implements the persistence contracts from `../planning`:

- strict Pydantic models for character passports, neutral readings, and block style plans;
- SQLAlchemy models for characters and speech examples;
- PostgreSQL enums and pgvector embeddings with 3072 dimensions;
- async repositories for profiles, examples, and style-RAG search.

Generation orchestration and HTTP CRUD are intentionally deferred until their contracts exist in `planning`.

This revision starts a new migration history and requires a fresh database. Back up any legacy data, then recreate the database/volume before running `alembic upgrade head`; deleted legacy revision IDs cannot be upgraded in place.

## Run

```bash
docker compose up -d postgres
docker compose run --rm app alembic upgrade head
docker compose up --build app
```

The health endpoint is `GET http://localhost:8000/health`.

## Tests

```bash
uv sync
uv run pytest -q
```

PostgreSQL integration tests use `natalai_test` and skip when that database is unavailable. The fixture refuses schema operations unless `APP_ENV=test` and the database name is `natalai_test` or ends with `_test`.
