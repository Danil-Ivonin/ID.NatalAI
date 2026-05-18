# NatalAI Backend MVP

NatalAI Backend MVP is the API and background worker for generating stylized natal-chart reports. It accepts birth data and a persona, builds a natal chart context, sends generation prompts through OpenRouter, and stores generation status/results in PostgreSQL.

## Stack

- Python 3.11
- FastAPI and Uvicorn for the HTTP API
- SQLAlchemy async ORM with asyncpg
- Alembic for database migrations
- PostgreSQL 16 for persistence
- Redis 7 and Celery for background generation jobs
- Pydantic Settings for environment configuration
- OpenRouter for AI model calls
- uv for dependency and command execution
- pytest for tests

## Configuration

Copy the example environment file and set your OpenRouter key:

```powershell
Copy-Item .env.example .env
```

Edit `.env` and fill:

```dotenv
OPENROUTER_API_KEY=your-real-openrouter-key
```

`OPENROUTER_API_KEY` is required for AI generation. Compose files can still be
rendered without a `.env`, but the worker/OpenRouter client fails fast before
generation if the key is empty.

The checked-in Docker Compose file injects container-friendly service URLs for PostgreSQL and Redis. If you run the API or worker directly on the host while PostgreSQL/Redis are running in Docker Compose, use localhost-based values:

```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/natalai
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
REDIS_URL=redis://localhost:6379/0
```

## Run With Docker Compose

Start PostgreSQL and Redis:

```powershell
docker compose up -d postgres redis
```

Run Alembic migrations:

```powershell
docker compose run --rm app alembic upgrade head
```

Seed prompt templates and the initial persona data:

```powershell
docker compose run --rm app python -m app.db.seed
```

Start the API and worker:

```powershell
docker compose up --build app worker
```

The API is available at `http://localhost:8000`.

## Run Locally

Install/sync dependencies:

```powershell
uv sync
```

Start only PostgreSQL and Redis in Docker Compose:

```powershell
docker compose up -d postgres redis
```

Make sure `.env` uses localhost URLs for host-run processes, then run migrations and seed data:

```powershell
uv run alembic upgrade head
uv run python -m app.db.seed
```

Start the API:

```powershell
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Start the worker in a second shell:

```powershell
uv run celery -A app.core.celery_app.celery_app worker --loglevel=info
```

## Generation Endpoint

List seeded personas and copy an active persona `id`:

```powershell
curl.exe http://localhost:8000/api/v1/personas
```

Create a generation job:

```powershell
curl.exe -X POST http://localhost:8000/api/v1/generations `
  -H "Content-Type: application/json" `
  -d '{
    "person_name": "Alex",
    "gender": "female",
    "birth_date": "1994-04-12",
    "birth_time": "08:30:00",
    "birth_place": {
      "city": "Moscow",
      "country": "RU",
      "lat": 55.7558,
      "lng": 37.6173,
      "timezone": "Europe/Moscow"
    },
    "persona_id": "replace-with-persona-id"
  }'
```

The response includes a `generation_id`. Check job status and result:

```powershell
curl.exe http://localhost:8000/api/v1/generations/replace-with-generation-id
```

## Tests

Run the full test suite:

```powershell
uv run pytest -v
```

Database integration tests are marked `db_integration` and use `DATABASE_URL`, defaulting to `postgresql+asyncpg://postgres:postgres@localhost:5432/natalai_test` in tests. They skip automatically if the PostgreSQL test database is unavailable or if `APP_ENV`/`DATABASE_URL` are not clearly test-scoped.

Useful targeted checks:

```powershell
uv run python -m py_compile app/main.py app/core/config.py app/services/prompt_builder.py app/workers/tasks.py
uv run python -m app.db.seed --dry-run
docker compose config
```

## Architecture Map

- `app/main.py`: FastAPI application setup and API router registration.
- `app/api/v1/`: HTTP endpoints for personas, prompt templates, and generation jobs.
- `app/core/`: configuration, logging, database session setup, Celery app, and shared exceptions.
- `app/db/`: SQLAlchemy models, Alembic migrations, and seed script.
- `app/domain/`: Pydantic schemas, enums, and domain models for personas, prompts, and generations.
- `app/repositories/`: database access layer for personas, prompt templates, and generations.
- `app/services/`: natal chart generation, prompt building, OpenRouter calls, persona context assembly, and AI generation orchestration.
- `app/workers/`: Celery tasks that process generation jobs asynchronously.
- `tests/`: unit, API, worker, seed, and optional PostgreSQL integration tests.
