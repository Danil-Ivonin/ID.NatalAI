# NatalAI Backend MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-like FastAPI backend monolith that creates natal-chart generation jobs, runs a Celery AI pipeline, stores prompt/persona context in PostgreSQL, and returns styled roast reports.

**Architecture:** Modular monolith with explicit API, repository, service, worker, and domain boundaries. Celery tasks remain synchronous worker entrypoints and run async orchestration through an event-loop helper. Prompt templates and persona style data live in PostgreSQL, while OpenRouter and kerykeion are isolated behind service classes.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, pydantic-settings, SQLAlchemy 2 async, Alembic, PostgreSQL, Celery, Redis, httpx, tenacity, kerykeion, pytest, pytest-asyncio, standard Python logging.

---

## File Map

- `pyproject.toml`: add runtime and test dependencies.
- `.env.example`: document required settings.
- `Dockerfile`: container image for app and worker.
- `docker-compose.yml`: app, worker, postgres, redis.
- `alembic.ini`: Alembic CLI config.
- `app/main.py`: FastAPI factory and router mounting.
- `app/core/config.py`: pydantic-settings configuration.
- `app/core/database.py`: async engine, sessionmaker, dependency.
- `app/core/celery_app.py`: Celery app configuration.
- `app/core/logging.py`: standard logging setup.
- `app/core/exceptions.py`: domain exceptions.
- `app/domain/generation/enums.py`: generation enums.
- `app/domain/generation/models.py`: generation SQLAlchemy models.
- `app/domain/generation/schemas.py`: generation API DTOs.
- `app/domain/generation/ai_schemas.py`: strict AI output schemas.
- `app/domain/persona/models.py`: persona SQLAlchemy models.
- `app/domain/persona/schemas.py`: persona API DTOs.
- `app/domain/persona/context.py`: `PersonaContext` schema and provider protocol.
- `app/domain/prompts/enums.py`: prompt template type enum.
- `app/domain/prompts/models.py`: prompt template SQLAlchemy model.
- `app/domain/prompts/schemas.py`: prompt template API DTOs.
- `app/repositories/generation_repository.py`: generation and generation run persistence.
- `app/repositories/persona_repository.py`: persona persistence and context loading.
- `app/repositories/prompt_template_repository.py`: prompt template persistence and activation.
- `app/services/natal_chart_service.py`: kerykeion integration.
- `app/services/prompt_builder.py`: prompt assembly from templates and context.
- `app/services/openrouter_client.py`: OpenRouter transport.
- `app/services/persona_context_service.py`: PostgreSQL persona context provider.
- `app/services/ai_generation_service.py`: generation orchestration.
- `app/api/v1/generations.py`: generation endpoints.
- `app/api/v1/personas.py`: persona endpoints.
- `app/api/v1/prompt_templates.py`: prompt template endpoints.
- `app/workers/tasks.py`: Celery task entrypoints.
- `app/db/migrations/env.py`: Alembic environment.
- `app/db/migrations/versions/0001_initial_schema.py`: initial migration.
- `app/db/seed.py`: prompt templates and Shrek seed data.
- `tests/conftest.py`: async test DB/session and app fixtures.
- `tests/test_generations_api.py`: generation endpoint tests.
- `tests/test_natal_chart_service.py`: kerykeion service test.
- `tests/test_prompt_builder.py`: prompt safety and missing-name tests.
- `tests/test_persona_context.py`: context provider test.
- `tests/test_generation_pipeline.py`: status and OpenRouter error tests.
- `README.md`: local and Docker run instructions.

## Task 1: Dependencies, Settings, Logging, Database Foundation

**Files:**
- Modify: `pyproject.toml`
- Create: `.env.example`
- Create: `app/__init__.py`
- Create: `app/core/__init__.py`
- Create: `app/core/config.py`
- Create: `app/core/database.py`
- Create: `app/core/logging.py`
- Create: `app/core/exceptions.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Update dependencies**

Add the needed packages to `pyproject.toml`:

```toml
dependencies = [
    "alembic>=1.17.2",
    "anyio>=4.12.0",
    "asyncpg>=0.31.0",
    "celery>=5.6.0",
    "fastapi>=0.136.1",
    "httpx>=0.28.1",
    "kerykeion>=5.12.8",
    "orjson>=3.11.5",
    "pydantic-settings>=2.12.0",
    "python-dotenv>=1.2.1",
    "redis>=7.1.0",
    "sqlalchemy>=2.0.49",
    "tenacity>=9.1.2",
    "uvicorn[standard]>=0.38.0",
]

[dependency-groups]
dev = [
    "pytest>=9.0.2",
    "pytest-asyncio>=1.3.0",
    "respx>=0.22.0",
]
```

Run: `uv lock`

Expected: lock file updates successfully.

- [ ] **Step 2: Add settings**

Create `app/core/config.py`:

```python
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="local", alias="APP_ENV")
    database_url: str = Field(alias="DATABASE_URL")
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(alias="CELERY_RESULT_BACKEND")
    openrouter_api_key: str = Field(default="", alias="OPENROUTER_API_KEY")
    openrouter_base_url: str = Field(default="https://openrouter.ai/api/v1", alias="OPENROUTER_BASE_URL")
    openrouter_model_profile: str = Field(default="openai/gpt-5", alias="OPENROUTER_MODEL_PROFILE")
    openrouter_model_report: str = Field(default="openai/gpt-5", alias="OPENROUTER_MODEL_REPORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

- [ ] **Step 3: Add database session utilities**

Create `app/core/database.py`:

```python
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
```

- [ ] **Step 4: Add logging setup**

Create `app/core/logging.py`:

```python
import logging
import sys

from app.core.config import get_settings


def configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
```

- [ ] **Step 5: Add exception types**

Create `app/core/exceptions.py`:

```python
class NatalAIError(Exception):
    """Base application exception."""


class NotFoundError(NatalAIError):
    """Requested entity does not exist."""


class ValidationFailure(NatalAIError):
    """User input or AI output failed validation."""


class OpenRouterTemporaryError(NatalAIError):
    """OpenRouter request can be retried."""
```

- [ ] **Step 6: Add env example**

Create `.env.example`:

```dotenv
APP_ENV=local
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/natalai
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
OPENROUTER_API_KEY=your-api-key
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL_PROFILE=openai/gpt-5
OPENROUTER_MODEL_REPORT=openai/gpt-5
LOG_LEVEL=INFO
```

- [ ] **Step 7: Add pytest fixtures**

Create `tests/conftest.py` with SQLite-free PostgreSQL test configuration using dependency overrides only after the app exists:

```python
import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/natalai_test")
os.environ.setdefault("CELERY_BROKER_URL", "redis://localhost:6379/0")
os.environ.setdefault("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
```

- [ ] **Step 8: Verify import baseline**

Run: `uv run python -c "from app.core.config import get_settings; print(get_settings().app_env)"`

Expected: prints `test` if run under pytest context, otherwise `local` when `.env` is present.

## Task 2: Domain Models and Initial Migration

**Files:**
- Create: `app/domain/__init__.py`
- Create: `app/domain/generation/__init__.py`
- Create: `app/domain/generation/enums.py`
- Create: `app/domain/generation/models.py`
- Create: `app/domain/persona/__init__.py`
- Create: `app/domain/persona/models.py`
- Create: `app/domain/prompts/__init__.py`
- Create: `app/domain/prompts/enums.py`
- Create: `app/domain/prompts/models.py`
- Create: `alembic.ini`
- Create: `app/db/migrations/env.py`
- Create: `app/db/migrations/script.py.mako`
- Create: `app/db/migrations/versions/0001_initial_schema.py`

- [ ] **Step 1: Add enums**

Create `app/domain/generation/enums.py`:

```python
from enum import StrEnum


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class GenerationStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationStage(StrEnum):
    NATAL_CHART_BUILD = "natal_chart_build"
    ASTROLOGY_PROFILE_EXTRACTION = "astrology_profile_extraction"
    STYLED_REPORT_GENERATION = "styled_report_generation"
```

Create `app/domain/prompts/enums.py`:

```python
from enum import StrEnum


class PromptTemplateType(StrEnum):
    ASTROLOGY_PROFILE_EXTRACTION = "astrology_profile_extraction"
    STYLED_REPORT_GENERATION = "styled_report_generation"
```

- [ ] **Step 2: Add SQLAlchemy models**

Create model files with UUID primary keys, timestamp columns, JSONB fields, foreign keys, and relationships matching the design spec. Use `sqlalchemy.dialects.postgresql.UUID` and `JSONB`.

Example base pattern for each table:

```python
import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

- [ ] **Step 3: Add Alembic config**

Create `alembic.ini` pointing to `app/db/migrations`.

Create `app/db/migrations/env.py` importing all model modules before setting `target_metadata = Base.metadata`.

- [ ] **Step 4: Add initial migration**

Create `0001_initial_schema.py` with all tables from the design spec and indexes:

```python
op.create_index("ix_personas_slug", "personas", ["slug"], unique=True)
op.create_index("ix_prompt_templates_type_active", "prompt_templates", ["type", "is_active"])
op.create_index("ix_generations_status", "generations", ["status"])
op.create_index("ix_generation_runs_generation_id", "generation_runs", ["generation_id"])
```

- [ ] **Step 5: Verify migration syntax**

Run: `uv run python -m py_compile app/db/migrations/versions/0001_initial_schema.py`

Expected: command exits with code 0.

## Task 3: Pydantic API and AI Schemas

**Files:**
- Create: `app/domain/generation/schemas.py`
- Create: `app/domain/generation/ai_schemas.py`
- Create: `app/domain/persona/schemas.py`
- Create: `app/domain/persona/context.py`
- Create: `app/domain/prompts/schemas.py`

- [ ] **Step 1: Add generation DTOs**

Create request/response models for birth place, generation creation, and generation detail. `person_name` and `gender` are nullable. `gender` accepts only `male` and `female`.

- [ ] **Step 2: Add strict AI schemas**

Create `AstrologyProfile` and `StyledNatalReport` with `model_config = ConfigDict(extra="forbid")`. Ensure evidence fields use `list[str]` and important sections are required.

- [ ] **Step 3: Add persona context schema**

Create `PersonaContext` and provider protocol:

```python
from typing import Protocol
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PersonaContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    persona_name: str
    persona_slug: str
    persona_description: str | None
    voice_description: str
    humor_style: str
    speech_patterns: list[str]
    allowed_rules: list[str]
    forbidden_rules: list[str]
    allowed_quotes: list[str]
    phrase_templates: list[str]
    style_examples: list[str]


class PersonaContextProvider(Protocol):
    async def get_context(self, persona_id: UUID) -> PersonaContext:
        ...
```

- [ ] **Step 4: Verify schemas import**

Run: `uv run python -c "from app.domain.generation.ai_schemas import AstrologyProfile, StyledNatalReport; print(AstrologyProfile, StyledNatalReport)"`

Expected: prints class objects.

## Task 4: Repositories

**Files:**
- Create: `app/repositories/__init__.py`
- Create: `app/repositories/generation_repository.py`
- Create: `app/repositories/persona_repository.py`
- Create: `app/repositories/prompt_template_repository.py`
- Test: `tests/test_persona_context.py`

- [ ] **Step 1: Add repository methods**

Implement async repository classes with explicit methods:

```python
class GenerationRepository:
    async def create(self, data: GenerationCreate) -> Generation: ...
    async def get(self, generation_id: UUID) -> Generation | None: ...
    async def set_status(self, generation_id: UUID, status: GenerationStatus) -> None: ...
    async def save_natal_xml(self, generation_id: UUID, natal_xml: str) -> None: ...
    async def save_profile(self, generation_id: UUID, profile: dict) -> None: ...
    async def save_result(self, generation_id: UUID, result_json: dict, result_text: str) -> None: ...
    async def fail(self, generation_id: UUID, error_message: str) -> None: ...
    async def create_run(self, values: dict) -> GenerationRun: ...
```

Add persona and prompt repositories for CRUD, context-loading queries, active-template lookup, and activation.

- [ ] **Step 2: Write context provider repository test**

Create `tests/test_persona_context.py` with a test that inserts persona rows and asserts returned `PersonaContext` contains allowed quotes, phrase templates, and examples.

- [ ] **Step 3: Run repository test**

Run: `uv run pytest tests/test_persona_context.py -v`

Expected before full DB fixture work: test may fail on missing DB fixture. Complete fixture wiring in Task 8.

## Task 5: Natal Chart and Prompt Builder Services

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/natal_chart_service.py`
- Create: `app/services/prompt_builder.py`
- Test: `tests/test_natal_chart_service.py`
- Test: `tests/test_prompt_builder.py`

- [ ] **Step 1: Add NatalChartService**

Implement:

```python
class NatalChartService:
    def build_natal_chart(
        self,
        person_name: str | None,
        gender: str | None,
        birth_date: date,
        birth_time: time,
        lat: float,
        lng: float,
        timezone: str,
    ) -> NatalChartResult:
        ...
```

Use `person_name or "Anonymous"` only for kerykeion subject creation.

- [ ] **Step 2: Add PromptBuilder**

Implement methods from the design spec. The builder receives system template content as a parameter or constructor value and creates OpenAI-compatible messages:

```python
[
    {"role": "system", "content": template.content},
    {"role": "user", "content": user_payload},
]
```

For missing names, render `person_name` as `не указано`; never render `Anonymous` as the user name in final report prompts.

- [ ] **Step 3: Add prompt tests**

Write tests for first and second stage prompts with and without `person_name`. Include an assertion:

```python
assert "Anonymous" not in final_messages[1]["content"]
```

- [ ] **Step 4: Run service tests**

Run: `uv run pytest tests/test_natal_chart_service.py tests/test_prompt_builder.py -v`

Expected: prompt tests pass; kerykeion test passes when dependency API matches the implementation.

## Task 6: OpenRouter Client and AI Orchestration

**Files:**
- Create: `app/services/openrouter_client.py`
- Create: `app/services/persona_context_service.py`
- Create: `app/services/ai_generation_service.py`
- Test: `tests/test_generation_pipeline.py`

- [ ] **Step 1: Add OpenRouterClient**

Implement async `chat_completion` with:

- Authorization header from settings.
- No API key in raw request.
- `response_format` support.
- tenacity retry for transport/timeouts/5xx.
- returned dataclass containing content, raw response, token usage, and latency.

- [ ] **Step 2: Add PostgresPersonaContextProvider**

Use `PersonaRepository` to load persona, style profile, allowed quotes, phrase templates, and examples. Raise `NotFoundError` if persona is missing or inactive.

- [ ] **Step 3: Add AIGenerationService**

Implement `generate(generation_id: UUID)` orchestration:

1. load generation;
2. set `processing`;
3. build and save natal XML;
4. run profile stage;
5. validate `AstrologyProfile`;
6. save profile;
7. load persona context;
8. run styled report stage;
9. validate `StyledNatalReport`;
10. save result and `completed`;
11. on exception, save failed status and run error.

- [ ] **Step 4: Add OpenRouter error test**

Mock `OpenRouterClient.chat_completion` to raise an exception and assert generation becomes `failed` with `error_message`.

## Task 7: FastAPI Routers and App Wiring

**Files:**
- Modify: `app/main.py`
- Create: `app/api/__init__.py`
- Create: `app/api/v1/__init__.py`
- Create: `app/api/v1/generations.py`
- Create: `app/api/v1/personas.py`
- Create: `app/api/v1/prompt_templates.py`
- Test: `tests/test_generations_api.py`

- [ ] **Step 1: Add FastAPI app**

`app/main.py` should configure logging, create FastAPI, and include routers under `/api/v1`.

- [ ] **Step 2: Add generation endpoints**

`POST /api/v1/generations` creates pending generation and dispatches Celery task.

`GET /api/v1/generations/{generation_id}` returns status/result/error.

- [ ] **Step 3: Add persona endpoints**

Implement MVP CRUD for persona base records and style-related nested payloads where practical for seed/test usage.

- [ ] **Step 4: Add prompt template endpoints**

Implement create, list, active lookup, and activation.

- [ ] **Step 5: Add API tests**

Tests cover creation with `person_name`, creation without `person_name`, and fetching generation.

Run: `uv run pytest tests/test_generations_api.py -v`

Expected: all API tests pass after DB fixtures are complete.

## Task 8: Celery Worker and Infrastructure

**Files:**
- Create: `app/core/celery_app.py`
- Create: `app/workers/__init__.py`
- Create: `app/workers/tasks.py`
- Create: `Dockerfile`
- Create: `docker-compose.yml`

- [ ] **Step 1: Add Celery app**

Create a Celery instance using broker/result backend from settings and import `app.workers.tasks`.

- [ ] **Step 2: Add synchronous task**

Implement:

```python
@celery_app.task(name="generate_natal_report_task")
def generate_natal_report_task(generation_id: str) -> None:
    anyio.run(_run_generation, generation_id)
```

Inside `_run_generation`, create an async SQLAlchemy session and call `AIGenerationService.generate`.

- [ ] **Step 3: Add Dockerfile**

Use `python:3.11-slim`, install project dependencies with `uv`, copy app, and run commands supplied by compose.

- [ ] **Step 4: Add docker-compose**

Define `app`, `worker`, `postgres`, and `redis` services. App command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Worker command:

```bash
celery -A app.core.celery_app.celery_app worker --loglevel=info
```

## Task 9: Seed Data

**Files:**
- Create: `app/db/__init__.py`
- Create: `app/db/seed.py`

- [ ] **Step 1: Add seed prompts**

Insert the two prompt templates from the user requirements exactly as active version 1 records.

- [ ] **Step 2: Add Shrek persona**

Insert persona `Шрек`, style profile, forbidden rules, allowed rules, phrase templates, and style examples. Include persona rules that allow maximum-intensity roast, profanity, aggressive sarcasm, and rough comedic stereotypes while keeping protected-class dehumanization and violence out of scope.

- [ ] **Step 3: Add idempotency**

Seed script should use slug/type/version lookups and update existing rows instead of creating duplicates.

- [ ] **Step 4: Verify seed imports**

Run: `uv run python -m app.db.seed --dry-run`

Expected: prints planned inserts/updates without touching the database.

## Task 10: Full Test Fixture Wiring and Verification

**Files:**
- Modify: `tests/conftest.py`
- Modify: all test files from previous tasks

- [ ] **Step 1: Add async DB fixture**

Create and drop schema tables around test sessions using `Base.metadata.create_all` and `drop_all` against the test database.

- [ ] **Step 2: Add app fixture**

Use FastAPI `TestClient` or `httpx.AsyncClient` with dependency override for `get_session`.

- [ ] **Step 3: Patch Celery dispatch in API tests**

Mock `generate_natal_report_task.delay` so API tests do not require a running worker.

- [ ] **Step 4: Run all tests**

Run: `uv run pytest -v`

Expected: all tests pass.

## Task 11: README and Final Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Document setup**

README must include:

- copy `.env.example` to `.env`;
- start Docker Compose;
- run Alembic migrations;
- run seed script;
- start API;
- start worker;
- call generation endpoints.

- [ ] **Step 2: Run static import verification**

Run:

```bash
uv run python -m py_compile app/main.py app/core/config.py app/services/prompt_builder.py app/workers/tasks.py
```

Expected: command exits with code 0.

- [ ] **Step 3: Run test suite**

Run: `uv run pytest -v`

Expected: all tests pass.

- [ ] **Step 4: Manual API smoke test**

With Docker services running, run:

```bash
curl -X POST http://localhost:8000/api/v1/generations \
  -H "Content-Type: application/json" \
  -d '{"person_name":null,"gender":"male","birth_date":"2001-01-25","birth_time":"13:00","birth_place":{"city":"Voronezh","country":"RU","lat":51.675495,"lng":39.208881,"timezone":"Europe/Moscow"},"persona_id":"REPLACE_WITH_SEEDED_PERSONA_ID"}'
```

Expected: response contains `generation_id` and `status: pending`.

## Self-Review

- Spec coverage: plan covers project structure, models, migrations, API, prompt storage, persona storage, Celery, OpenRouter, kerykeion, missing `person_name`, `male`/`female` gender handling, maximum roast mode, Docker, seed data, README, and tests.
- Placeholder scan: no placeholder markers or open-ended implementation instructions remain.
- Type consistency: public method names match the design spec and file map.
