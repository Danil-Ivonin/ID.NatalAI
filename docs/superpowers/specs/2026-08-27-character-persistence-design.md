# Character Persistence Design

## Goal

Replace the deleted legacy persistence layer with a new PostgreSQL-backed character and style-example model defined by `planning/`. Legacy personas, prompt templates, generations, APIs, and generation services are not compatible and are not preserved.

## Source of Truth

- `planning/character_profile.md`
- `planning/character_examples.md`
- `planning/neutral_chart_reading.md`
- `planning/style_taxonomy_and_planner.md`
- `planning/generation_prompts_and_costs.md`

Where prose conflicts, the stricter repeated validation rule wins. Neutral blocks may contain zero to five hooks because that range is repeated in the generation instruction and validation section.

## Database

The initial Alembic migration creates the `vector` extension, the PostgreSQL enums `character_emotion`, `humor_type`, and `speech_pattern`, and two tables.

`characters` contains a bigint identity primary key, a required name, and one required JSONB `profile` document. The document contains `core`, `astrology_position`, `reader_relationship`, `voice`, `humor`, `monologue_structure`, and `do_not`; `id` and `name` remain relational columns.

`character_examples` follows `planning/character_examples.md`: bigint identity primary key, cascading `character_id`, raw and clean text, context, emotion, rhetorical function, enum arrays for humor and speech patterns, nullable `vector(3072)`, and an active flag defaulting to true. It has the specified character ID index.

The development PostgreSQL container uses a PostgreSQL 18 image that includes pgvector. Python uses the installed SQLAlchemy stack plus the `pgvector` package for correct asyncpg binding and distance expressions.

## Pydantic Contracts

All structured-output and persistence schemas forbid extra fields. The character passport is represented by focused nested models matching the planning JSON. Create schemas omit generated IDs; read schemas include them.

`NeutralChartReading` validates:

- exactly four ordered and unique blocks: `general`, `love`, `work_money`, `inner_demons`;
- zero to five hooks per block;
- unique fact and hook IDs across the document;
- hook references only to facts in the same block;
- one or more evidence records per fact;
- the documented enum vocabularies.

Evidence is a discriminated union for placement, aspect, house, and angle records. The house and angle shapes stay minimal and consistent: house evidence contains `house`; angle evidence contains `angle`.

`BlockStylePlan` validates exact one-time coverage of caller-provided hooks through an explicit `validate_for(block)` method. Each hook plan has one valid emotion, at most two humor types, and at most three speech patterns. Callback journal validation belongs to the future orchestration service because the journal contract is not specified.

## Repository Contracts

`CharacterRepository` provides `create`, `get_profile`, and `replace_profile`. Replacement is whole-document and atomic; partial nested updates are intentionally excluded.

`CharacterExampleRepository` provides `create`, `set_embedding`, `set_active`, and `search`. Repositories flush but never commit.

Search handles one hook at a time and always constrains candidates by character, active state, non-null embedding, and excluded IDs. It orders by cosine distance adjusted by a small fixed bonus for matching emotion and overlapping humor/speech tags. This is a soft ranking bonus, never a filter. Cross-hook merge, deduplication, ensuring representation for every hook, and the final five-to-eight-example cap belong to the future orchestration service.

Missing records return `None`. Invalid IDs, enum values, required strings, tag limits, and embeddings whose length is not 3072 fail at the Pydantic boundary.

## Legacy Cleanup

Obsolete API routes, generation services, workers, prompt models, and tests depend on the intentionally removed legacy domain. They are removed instead of adapted. The application retains a minimal FastAPI shell and database configuration so the new layer imports and Alembic runs cleanly.

## Testing

Implementation follows red-green-refactor. Tests cover strict passport parsing, neutral-reading invariants, style-plan coverage, ORM metadata, repository mutation behavior, compiled search constraints/ranking, and PostgreSQL integration when the configured test database is available. Alembic upgrade/downgrade and the complete test suite are run before completion.

## Explicitly Deferred

- Generation tables and job status persistence
- Prompt-template persistence
- Character/example HTTP APIs
- Embedding API calls
- Multi-hook retrieval orchestration
- Neutral reader, style planner, author, validator, and correction services

These are added only when their contracts exist in `planning/`.
