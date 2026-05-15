# NatalAI Backend MVP Design

## Context

NatalAI is a backend monolith for an AI service that generates a personalized humorous natal-chart report in the style of a selected character. The backend accepts birth data, builds a natal chart, extracts a structured astrology profile with AI, and then transforms that profile into a final styled report using persona data from PostgreSQL.

The MVP intentionally excludes Telegram bot integration, payments, tariffs, streaming, multilingual modes, geocoding, a full admin panel, and Qdrant/RAG as a required dependency.

## Recommended Approach

Use a modular monolith with FastAPI, async SQLAlchemy, PostgreSQL, Celery, Redis, OpenRouter, and kerykeion.

Celery tasks will remain synchronous `def` tasks. Long-running business logic will still use async services internally via an event-loop helper such as `anyio.run`. This keeps Celery worker behavior conventional and avoids lifecycle issues with async event loops, SQLAlchemy async sessions, broker retries, and worker pools. OpenRouter and database access remain async inside the service layer.

## Project Structure

```text
app/
  main.py

  api/
    v1/
      generations.py
      personas.py
      prompt_templates.py

  core/
    config.py
    database.py
    celery_app.py
    logging.py
    exceptions.py

  domain/
    generation/
      enums.py
      models.py
      schemas.py
      ai_schemas.py
    persona/
      models.py
      schemas.py
      context.py
    prompts/
      enums.py
      models.py
      schemas.py

  repositories/
    generation_repository.py
    persona_repository.py
    prompt_template_repository.py

  services/
    natal_chart_service.py
    prompt_builder.py
    openrouter_client.py
    ai_generation_service.py
    persona_context_service.py

  workers/
    tasks.py

  db/
    migrations/
    seed.py

tests/
```

## API

### Generations

`POST /api/v1/generations`

Creates a generation record with `pending` status, dispatches `generate_natal_report_task(generation_id)`, and returns the generation id and status.

`GET /api/v1/generations/{generation_id}`

Returns generation status, result text if completed, error message if failed, and timestamps.

### Personas

`POST /api/v1/personas`

`GET /api/v1/personas`

`GET /api/v1/personas/{persona_id}`

`PATCH /api/v1/personas/{persona_id}`

### Prompt Templates

`POST /api/v1/prompt-templates`

`GET /api/v1/prompt-templates`

`GET /api/v1/prompt-templates/active?type=...`

`POST /api/v1/prompt-templates/{template_id}/activate`

Activation deactivates all other templates of the same type, so only one active template exists per prompt type.

## Database Schema

### personas

- `id` UUID primary key
- `name` string
- `slug` string unique
- `description` text nullable
- `is_active` bool
- `created_at`
- `updated_at`

### persona_style_profiles

- `id` UUID primary key
- `persona_id` foreign key to `personas.id`
- `voice_description` text
- `humor_style` text
- `speech_patterns` jsonb
- `forbidden_rules` jsonb
- `allowed_rules` jsonb
- `created_at`
- `updated_at`

### persona_quotes

- `id` UUID primary key
- `persona_id` foreign key to `personas.id`
- `text` text
- `usage_context` string nullable
- `is_allowed` bool
- `created_at`
- `updated_at`

### persona_phrase_templates

- `id` UUID primary key
- `persona_id` foreign key to `personas.id`
- `type` string
- `template` text
- `usage` string nullable
- `created_at`
- `updated_at`

### persona_style_examples

- `id` UUID primary key
- `persona_id` foreign key to `personas.id`
- `title` string
- `text` text
- `tags` jsonb
- `created_at`
- `updated_at`

### prompt_templates

- `id` UUID primary key
- `name` string
- `type` string enum: `astrology_profile_extraction`, `styled_report_generation`
- `version` integer
- `content` text
- `is_active` bool
- `metadata` jsonb
- `created_at`
- `updated_at`

### generations

- `id` UUID primary key
- `person_name` string nullable
- `gender` string nullable; allowed values: `male`, `female`
- `birth_date` date
- `birth_time` time
- `birth_city` string
- `birth_country` string
- `birth_lat` float
- `birth_lng` float
- `birth_timezone` string
- `persona_id` foreign key to `personas.id`
- `status` string enum: `pending`, `processing`, `completed`, `failed`
- `natal_xml` text nullable
- `astrology_profile_json` jsonb nullable
- `result_json` jsonb nullable
- `result_text` text nullable
- `error_message` text nullable
- `created_at`
- `updated_at`
- `completed_at` nullable

### generation_runs

- `id` UUID primary key
- `generation_id` foreign key to `generations.id`
- `stage` string enum: `natal_chart_build`, `astrology_profile_extraction`, `styled_report_generation`
- `provider` string
- `model` string
- `prompt_template_id` foreign key to `prompt_templates.id` nullable
- `prompt_template_version` integer nullable
- `input_tokens` integer nullable
- `output_tokens` integer nullable
- `raw_request` jsonb nullable
- `raw_response` jsonb nullable
- `error_message` text nullable
- `latency_ms` integer nullable
- `created_at`

## Generation Flow

1. API receives `POST /api/v1/generations`.
2. Request is validated with Pydantic v2.
3. Persona existence and active status are checked.
4. A `Generation` is created with `pending` status.
5. Celery task `generate_natal_report_task(generation_id)` is dispatched.
6. API returns `{ "generation_id": "...", "status": "pending" }`.
7. Worker sets status to `processing`.
8. `NatalChartService` builds natal chart XML with kerykeion and stores `natal_xml`.
9. Worker records a `generation_runs` entry for `natal_chart_build`.
10. Active `astrology_profile_extraction` prompt template is loaded from PostgreSQL.
11. `PromptBuilder` builds the first-stage OpenRouter messages.
12. `OpenRouterClient` calls OpenRouter with JSON Schema response format.
13. Response is validated as `AstrologyProfile`.
14. `astrology_profile_json` is saved.
15. Persona context is loaded through `PersonaContextProvider`.
16. Active `styled_report_generation` prompt template is loaded.
17. `PromptBuilder` builds the final report prompt.
18. `OpenRouterClient` calls OpenRouter with structured response format.
19. Response is validated as `StyledNatalReport`.
20. `result_json` and `result_text` are saved.
21. Generation status becomes `completed`.

If an error occurs after dispatch, the worker stores the error in `generation_runs` and `generations.error_message`, logs the failure, and sets status to `failed`.

## NatalChartService

`NatalChartService` accepts `person_name`, `gender`, date, time, latitude, longitude, and timezone.

For kerykeion, a technical subject name is required:

```python
chart_subject_name = person_name or "Anonymous"
```

`Anonymous` is never treated as the user's real name and must not be used in final user-facing text. Tests will verify that when `person_name` is missing, the final prompt does not present `Anonymous` as a user name.

`gender` is not needed for natal chart construction.

## Gender Handling

The API supports only `male` and `female` for `gender`, and the field remains optional and nullable.

For this entertainment product, gender may be used in the final styled-report stage for grammar and comedic stereotypical framing. The final report should support the harshest allowed roast mode: profanity, aggressive sarcasm, toxic character voice, dark humor, rude jokes, and sharp comedic stereotypes when the selected persona style allows it. Gender framing may be intentionally rough and stereotypical as part of the comedic voice, but it must not override astrology-profile facts. The first AI stage should not infer core chart psychology from gender alone; astrology data remains the source of the structured profile.

The product supports maximum-intensity roast-style output within safety boundaries: profanity, harsh jokes, insulting comedic phrasing, and explicit language are allowed. The hard stop is dehumanizing attacks, discriminatory hate against protected groups, or encouragement of real-world violence. The target of the joke is the user's chart/persona interpretation, behavior patterns, contradictions, and comedic archetype, not a protected identity group.

## Person Name Handling

`person_name` is optional and nullable.

If present, it may be used naturally in prompts and final text.

If absent:

- the chart still builds using the technical kerykeion name `Anonymous`;
- prompts must say that the name is not provided;
- final report must not invent a name;
- final report must not use `Anonymous`.

## Prompt Templates

System prompts are stored in PostgreSQL in `prompt_templates`. Business logic does not hardcode system prompt text.

Seed data creates:

- `astrology_profile_extraction`, version 1, active
- `styled_report_generation`, version 1, active

During generation, `generation_runs` records the prompt template id and version used by each AI stage.

## PromptBuilder

`PromptBuilder` has two public methods:

```python
build_astrology_profile_prompt(
    natal_xml: str,
    person_name: str | None,
    gender: str | None,
) -> list[dict]

build_styled_report_prompt(
    astrology_profile_json: dict,
    persona_context: PersonaContext,
    person_name: str | None,
    gender: str | None,
) -> list[dict]
```

The first prompt asks AI to analyze natal XML and return strict JSON matching `AstrologyProfile`.

The second prompt uses only `astrology_profile_json` as the factual source and `PersonaContext` as the style source. It may use allowed quotes, phrase templates, style examples, profanity, maximum-intensity roast phrasing, insulting comedic comparisons, dark humor, and comedic stereotypes if allowed by persona rules, but must not copy long protected fragments or claim to be a real person.

## AI Structured Output

First-stage schema: `AstrologyProfile`.

Key sections:

- `subject`
- `chart_core`
- `important_configurations`
- `sections`
- `cross_connections`
- `generation_brief`

Models use `extra="forbid"`. Evidence fields are required lists of strings explaining which astrological data supports each conclusion.

Second-stage schema: `StyledNatalReport`.

Fields:

- `title`
- `intro`
- `general`
- `love_and_sex`
- `career_and_money`
- `demons`
- `final_summary`

Each report section has `title` and `text`.

## OpenRouterClient

`OpenRouterClient` is the only component that calls OpenRouter.

Responsibilities:

- read API key from settings;
- use `httpx.AsyncClient`;
- support retries through `tenacity`;
- support JSON Schema response format;
- measure latency;
- extract token usage when provider returns it;
- return raw response and normalized metadata;
- avoid logging API keys and full prompts.

## Persona Context

Persona style data is structured, not stored as one large string.

Pydantic schema `PersonaContext` includes:

- `persona_name`
- `persona_slug`
- `persona_description`
- `voice_description`
- `humor_style`
- `speech_patterns`
- `allowed_rules`
- `forbidden_rules`
- `allowed_quotes`
- `phrase_templates`
- `style_examples`

Interface:

```python
class PersonaContextProvider:
    async def get_context(self, persona_id: UUID) -> PersonaContext:
        ...
```

MVP implementation:

```python
class PostgresPersonaContextProvider(PersonaContextProvider):
    ...
```

Future extension point:

```python
class QdrantPersonaContextProvider(PersonaContextProvider):
    ...
```

Qdrant is not implemented in the MVP.

## Logging

Use standard Python logging in `app/core/logging.py`.

Log structured fields where practical:

- `generation_id`
- `stage`
- `persona_id`
- `model`
- `provider`
- `latency_ms`
- `status`
- `error_type`
- `error_message`

Do not log:

- `OPENROUTER_API_KEY`
- full raw prompts in normal application logs
- full `natal_xml`
- unnecessary personal data

Raw request and response payloads may be stored in `generation_runs` without API keys.

## Configuration

Settings use `pydantic-settings`.

Required environment variables:

- `APP_ENV`
- `DATABASE_URL`
- `REDIS_URL`
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL_PROFILE`
- `OPENROUTER_MODEL_REPORT`
- `OPENROUTER_BASE_URL`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `LOG_LEVEL`

## Docker Compose

Services:

- `app`: FastAPI via uvicorn
- `worker`: Celery worker
- `postgres`: PostgreSQL 16
- `redis`: Redis 7

## Seed Data

Seed script creates:

1. active prompt template `astrology_profile_extraction` v1;
2. active prompt template `styled_report_generation` v1;
3. test persona `Шрек` with structured style profile, phrase templates, rules, and examples.

## Testing

Minimum tests:

- create generation;
- create generation without `person_name`;
- get generation;
- `NatalChartService` with fixed latitude, longitude, and timezone;
- first-stage `PromptBuilder`;
- first-stage `PromptBuilder` without `person_name`;
- second-stage `PromptBuilder`;
- second-stage `PromptBuilder` without `person_name`;
- `PersonaContextProvider`;
- generation status transitions;
- OpenRouter error handling;
- `Anonymous` does not appear in the final prompt as the user's name when `person_name` is missing.

## Implementation Notes

The MVP should be production-like but intentionally small. Responsibilities must remain separated:

- API routers handle HTTP and DTOs.
- Repositories handle database access.
- Services handle business logic.
- `NatalChartService` handles kerykeion only.
- `PromptBuilder` handles prompt assembly only.
- `OpenRouterClient` handles AI transport only.
- Celery worker orchestrates the long-running pipeline.
