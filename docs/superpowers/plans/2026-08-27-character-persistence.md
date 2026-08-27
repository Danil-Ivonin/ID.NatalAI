# Character Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the character passport, neutral-reading/style-plan contracts, pgvector-backed character examples, and the minimum repositories described by `planning/`.

**Architecture:** Store each character passport as one validated JSONB document and each searchable speech example as a relational row with native PostgreSQL enums and `vector(3072)`. Keep SQLAlchemy inside repositories and return strict Pydantic models at the boundary; remove the incompatible legacy application surface instead of adapting it.

**Tech Stack:** Python 3.11+, Pydantic 2, SQLAlchemy 2 async, PostgreSQL 18, pgvector, Alembic, pytest

**Spec:** `docs/superpowers/specs/2026-08-27-character-persistence-design.md`

## Global Constraints

- `planning/` is the source of truth; legacy Persona/Generation/PromptTemplate compatibility is forbidden.
- Embeddings are exactly 3072 floats for `text-embedding-3-large`.
- Neutral readings contain exactly `general`, `love`, `work_money`, and `inner_demons` in that order, with zero to five hooks per block.
- Repositories flush but never commit.
- Search always filters by character, active state, non-null embedding, and excluded IDs; enum matches affect ranking but never eligibility.
- Do not implement generation jobs, prompt templates, HTTP CRUD, embedding calls, or multi-hook orchestration.

---

### Task 1: Strict domain contracts

**Files:**
- Create: `app/domain/characters/__init__.py`
- Create: `app/domain/characters/enums.py`
- Create: `app/domain/characters/schemas.py`
- Create: `app/domain/readings/__init__.py`
- Create: `app/domain/readings/schemas.py`
- Test: `tests/test_character_schemas.py`
- Test: `tests/test_reading_schemas.py`

**Interfaces:**
- Consumes: the JSON contracts and exact enum values in `planning/`.
- Produces: `CharacterEmotion`, `HumorType`, `SpeechPattern`, `CharacterProfileCreate`, `CharacterProfile`, `CharacterExampleCreate`, `CharacterExample`, `CharacterExampleEmbedding`, `CharacterExampleSearch`, `NeutralChartReading`, `NeutralBlock`, `BlockStylePlan`, and `BlockStylePlan.validate_for(block)`.

- [ ] **Step 1: Write failing character-schema tests**

```python
def test_character_profile_matches_planning_contract():
    profile = CharacterProfile.model_validate(VALID_PROFILE)
    assert profile.character_id == 1
    assert profile.voice.directness == "Прямо"

def test_character_example_enforces_embedding_and_tag_limits():
    with pytest.raises(ValidationError):
        CharacterExampleCreate(**VALID_EXAMPLE, embedding=[0.0] * 3071)
    with pytest.raises(ValidationError):
        CharacterExampleSearch(
            character_id=1,
            embedding=[0.0] * 3072,
            emotion="calm",
            humor_types=["irony", "sarcasm", "deadpan"],
        )
```

- [ ] **Step 2: Run the character-schema tests and verify RED**

Run: `uv run pytest tests/test_character_schemas.py -q`

Expected: collection fails because `app.domain.characters` does not exist.

- [ ] **Step 3: Implement character enums and schemas**

Use `StrEnum` for the three exact planning vocabularies. Use a shared strict base with `ConfigDict(extra="forbid")`, constrained non-blank strings, and this boundary shape:

```python
Embedding = Annotated[list[float], Field(min_length=3072, max_length=3072)]

class CharacterProfileCreate(CharacterProfileBody):
    name: NonBlankStr

class CharacterProfile(CharacterProfileCreate):
    character_id: int = Field(gt=0)

class CharacterExampleCreate(StrictModel):
    character_id: int = Field(gt=0)
    raw_text: NonBlankStr
    clean_text: NonBlankStr
    context: NonBlankStr
    emotion: CharacterEmotion
    rhetorical_function: NonBlankStr
    humor_types: list[HumorType] = Field(default_factory=list, max_length=2)
    speech_patterns: list[SpeechPattern] = Field(default_factory=list, max_length=3)
    embedding: Embedding | None = None
    active: bool = True

class CharacterExampleSearch(StrictModel):
    character_id: int = Field(gt=0)
    embedding: Embedding
    emotion: CharacterEmotion
    humor_types: list[HumorType] = Field(default_factory=list, max_length=2)
    speech_patterns: list[SpeechPattern] = Field(default_factory=list, max_length=3)
    exclude_ids: set[int] = Field(default_factory=set)
    limit: int = Field(default=8, ge=1, le=100)
```

- [ ] **Step 4: Run character-schema tests and verify GREEN**

Run: `uv run pytest tests/test_character_schemas.py -q`

Expected: all character-schema tests pass.

- [ ] **Step 5: Write failing neutral-reading and style-plan tests**

```python
def test_neutral_reading_requires_ordered_unique_blocks():
    payload = valid_reading_payload()
    payload["blocks"] = list(reversed(payload["blocks"]))
    with pytest.raises(ValidationError, match="general, love, work_money, inner_demons"):
        NeutralChartReading.model_validate(payload)

def test_hook_must_reference_fact_in_same_block():
    payload = valid_reading_payload()
    payload["blocks"][0]["hooks"][0]["fact_ids"] = ["missing"]
    with pytest.raises(ValidationError, match="missing"):
        NeutralChartReading.model_validate(payload)

def test_style_plan_covers_every_hook_once():
    block = NeutralBlock.model_validate(valid_reading_payload()["blocks"][0])
    plan = BlockStylePlan.model_validate(valid_plan_payload())
    assert plan.validate_for(block) is plan
```

- [ ] **Step 6: Run reading tests and verify RED**

Run: `uv run pytest tests/test_reading_schemas.py -q`

Expected: collection fails because `app.domain.readings` does not exist.

- [ ] **Step 7: Implement neutral-reading and style-plan schemas**

Use discriminated evidence types and after-validators for document invariants:

```python
Evidence = Annotated[
    PlacementEvidence | AspectEvidence | HouseEvidence | AngleEvidence,
    Field(discriminator="type"),
]

class NeutralChartReading(StrictModel):
    subject: Subject
    blocks: list[NeutralBlock] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_document(self) -> Self:
        expected = [BlockId.GENERAL, BlockId.LOVE, BlockId.WORK_MONEY, BlockId.INNER_DEMONS]
        if [block.id for block in self.blocks] != expected:
            raise ValueError("blocks must be ordered: general, love, work_money, inner_demons")
        # Enforce global fact/hook ID uniqueness and same-block hook references.
        return self

class BlockStylePlan(StrictModel):
    block_arc: NonBlankStr
    hook_plans: list[HookStylePlan]

    def validate_for(self, block: NeutralBlock) -> Self:
        if Counter(plan.hook_id for plan in self.hook_plans) != Counter(hook.id for hook in block.hooks):
            raise ValueError("style plan must cover every block hook exactly once")
        return self
```

- [ ] **Step 8: Run all domain tests and commit**

Run: `uv run pytest tests/test_character_schemas.py tests/test_reading_schemas.py -q`

Expected: all tests pass.

Commit:

```bash
git add app/domain/characters app/domain/readings tests/test_character_schemas.py tests/test_reading_schemas.py
git commit -m "feat: add character and reading contracts"
```

---

### Task 2: ORM metadata and initial pgvector migration

**Files:**
- Create: `app/domain/characters/models.py`
- Create: `app/db/models.py`
- Create: `app/db/migrations/versions/0001_character_persistence.py`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `docker-compose.yml`
- Test: `tests/test_database_models.py`

**Interfaces:**
- Consumes: Task 1 enums and PostgreSQL connection configuration.
- Produces: ORM `Character`, ORM `CharacterExample`, `Base.metadata` registry, PostgreSQL enums, pgvector extension, and two migrated tables.

- [ ] **Step 1: Write the failing metadata test**

```python
def test_metadata_contains_only_character_tables():
    import app.db.models  # noqa: F401
    assert sorted(Base.metadata.tables) == ["character_examples", "characters"]
    examples = Base.metadata.tables["character_examples"]
    assert examples.c.embedding.type.dim == 3072
    assert "character_examples_character_id_idx" in {index.name for index in examples.indexes}
```

- [ ] **Step 2: Run metadata test and verify RED**

Run: `uv run pytest tests/test_database_models.py -q`

Expected: fails because `app.db.models` and character ORM models do not exist.

- [ ] **Step 3: Add pgvector and implement ORM models**

Add `pgvector` to project dependencies, regenerate `uv.lock`, and map the documented schema:

```python
class Character(Base):
    __tablename__ = "characters"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    profile: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

class CharacterExample(Base):
    __tablename__ = "character_examples"
    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    character_id: Mapped[int] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), nullable=False, index=False
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    clean_text: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[str] = mapped_column(Text, nullable=False)
    emotion: Mapped[CharacterEmotion] = mapped_column(CHARACTER_EMOTION, nullable=False)
    rhetorical_function: Mapped[str] = mapped_column(Text, nullable=False)
    humor_types: Mapped[list[HumorType]] = mapped_column(
        ARRAY(HUMOR_TYPE), server_default="{}", nullable=False
    )
    speech_patterns: Mapped[list[SpeechPattern]] = mapped_column(
        ARRAY(SPEECH_PATTERN), server_default="{}", nullable=False
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(3072))
    active: Mapped[bool] = mapped_column(Boolean, server_default=true(), nullable=False)
```

Declare the index explicitly as `character_examples_character_id_idx`. Registry module imports and exports both models.

- [ ] **Step 4: Implement one clean initial migration and pgvector Compose image**

The migration creates the extension/types/tables/index in dependency order and reverses tables/types in downgrade order. Change only the PostgreSQL image to `pgvector/pgvector:pg18`; leave unrelated user-edited settings intact until legacy cleanup.

- [ ] **Step 5: Run metadata test and migration SQL checks**

Run:

```bash
uv run pytest tests/test_database_models.py -q
uv run alembic upgrade head --sql > /tmp/natalai-upgrade.sql
rg "CREATE EXTENSION|CREATE TYPE character_emotion|vector\(3072\)|character_examples_character_id_idx" /tmp/natalai-upgrade.sql
```

Expected: metadata tests pass and all four migration constructs appear.

- [ ] **Step 6: Commit ORM and migration**

```bash
git add app/domain/characters/models.py app/db/models.py app/db/migrations/versions pyproject.toml uv.lock docker-compose.yml tests/test_database_models.py
git commit -m "feat: add pgvector character schema"
```

---

### Task 3: Minimal async repositories

**Files:**
- Create: `app/repositories/character_repository.py`
- Create: `app/repositories/character_example_repository.py`
- Modify: `app/repositories/__init__.py`
- Test: `tests/test_character_repositories.py`

**Interfaces:**
- Consumes: Task 1 schemas and Task 2 ORM models.
- Produces:
  - `CharacterRepository.create(data: CharacterProfileCreate) -> CharacterProfile`
  - `CharacterRepository.get_profile(character_id: int) -> CharacterProfile | None`
  - `CharacterRepository.replace_profile(character_id: int, data: CharacterProfileCreate) -> CharacterProfile | None`
  - `CharacterExampleRepository.create(data: CharacterExampleCreate) -> CharacterExample`
  - `CharacterExampleRepository.set_embedding(example_id: int, data: CharacterExampleEmbedding) -> CharacterExample | None`
  - `CharacterExampleRepository.set_active(example_id: int, active: bool) -> CharacterExample | None`
  - `CharacterExampleRepository.search(data: CharacterExampleSearch) -> list[CharacterExample]`

- [ ] **Step 1: Write failing character repository tests**

```python
@pytest.mark.asyncio
async def test_character_repository_round_trips_typed_profile():
    session = FakeSession()
    repository = CharacterRepository(session)
    created = await repository.create(valid_profile_create())
    assert created.name == "Имя персонажа"
    assert session.flushed == 1

@pytest.mark.asyncio
async def test_replace_profile_returns_none_when_character_missing():
    repository = CharacterRepository(FakeSession(get_result=None))
    assert await repository.replace_profile(999, valid_profile_create()) is None
```

- [ ] **Step 2: Run repository tests and verify RED**

Run: `uv run pytest tests/test_character_repositories.py -q`

Expected: import fails because the new repositories do not exist.

- [ ] **Step 3: Implement character repository mapping**

Map the JSONB body in two small private static methods and use `session.get`, `add`, and `flush`; never call `commit` or `refresh`.

```python
@staticmethod
def _to_profile(row: Character) -> CharacterProfile:
    return CharacterProfile(character_id=row.id, name=row.name, **row.profile)
```

- [ ] **Step 4: Add failing example mutation and search-query tests**

```python
@pytest.mark.asyncio
async def test_search_builds_required_filters_and_soft_ranking():
    session = CapturingSession([])
    await CharacterExampleRepository(session).search(valid_search())
    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "character_examples.character_id" in sql
    assert "character_examples.active IS true" in sql
    assert "character_examples.embedding IS NOT NULL" in sql
    assert "<=>" in sql
    assert "&&" in sql
    assert "NOT IN" in sql
```

- [ ] **Step 5: Run the new test and verify RED for missing search behavior**

Run: `uv run pytest tests/test_character_repositories.py::test_search_builds_required_filters_and_soft_ranking -q`

Expected: fails before the search method implements all required clauses.

- [ ] **Step 6: Implement example mutation and search**

Use a fixed maximum bonus of `0.10`:

```python
distance = CharacterExample.embedding.cosine_distance(data.embedding)
bonus = (
    case((CharacterExample.emotion == data.emotion, 0.05), else_=0.0)
    + case((CharacterExample.humor_types.overlap(data.humor_types), 0.025), else_=0.0)
    + case((CharacterExample.speech_patterns.overlap(data.speech_patterns), 0.025), else_=0.0)
)
statement = (
    select(CharacterExample)
    .where(
        CharacterExample.character_id == data.character_id,
        CharacterExample.active.is_(True),
        CharacterExample.embedding.is_not(None),
    )
    .order_by(distance - bonus, CharacterExample.id)
    .limit(data.limit)
)
```

Only add overlap terms for non-empty requested arrays, and only add `NOT IN` when exclusions are non-empty.

- [ ] **Step 7: Run repository tests and commit**

Run: `uv run pytest tests/test_character_repositories.py -q`

Expected: all repository tests pass.

Commit:

```bash
git add app/repositories tests/test_character_repositories.py
git commit -m "feat: add character repositories"
```

---

### Task 4: Remove incompatible legacy surface and verify the clean project

**Files:**
- Delete: `app/api/v1/generations.py`
- Delete: `app/api/v1/personas.py`
- Delete: `app/api/v1/prompt_templates.py`
- Delete: `app/core/celery_app.py`
- Delete: `app/domain/prompts/`
- Delete: `app/services/`
- Delete: `app/workers/`
- Delete: legacy test files under `tests/`
- Modify: `app/main.py`
- Modify: `app/core/config.py`
- Modify: `docker-compose.yml`
- Modify: `Dockerfile`
- Modify: `README.md`
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Test: `tests/conftest.py`
- Test: `tests/test_app.py`
- Test: `tests/test_migrations.py`

**Interfaces:**
- Consumes: Tasks 1–3 and the existing async database setup.
- Produces: importable minimal FastAPI app, persistence-only dependencies/Compose stack, safe optional PostgreSQL integration tests, and clean project documentation.

- [ ] **Step 1: Write failing minimal-app and integration tests**

```python
def test_app_starts_without_legacy_routes():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}

@pytest.mark.db_integration
@pytest.mark.asyncio
async def test_repository_search_persists_pgvector_rows(db_session):
    characters = CharacterRepository(db_session)
    examples = CharacterExampleRepository(db_session)
    character = await characters.create(valid_profile_create())
    first = await examples.create(
        valid_example_create(
            character_id=character.character_id,
            emotion=CharacterEmotion.CALM,
            embedding=[1.0] + [0.0] * 3071,
        )
    )
    second = await examples.create(
        valid_example_create(
            character_id=character.character_id,
            emotion=CharacterEmotion.ANGER,
            embedding=[1.0] + [0.0] * 3071,
        )
    )
    found = await examples.search(
        CharacterExampleSearch(
            character_id=character.character_id,
            embedding=[1.0] + [0.0] * 3071,
            emotion=CharacterEmotion.CALM,
            limit=2,
        )
    )
    assert [item.id for item in found] == [first.id, second.id]
```

- [ ] **Step 2: Run the complete suite and verify RED from legacy imports**

Run: `uv run pytest -q`

Expected: collection fails on removed legacy domain imports.

- [ ] **Step 3: Delete obsolete code/tests and reduce the app shell**

Keep only a native health route:

```python
app = FastAPI(title="NatalAI Backend")

@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

Reduce settings to `APP_ENV`, `DATABASE_URL`, and `LOG_LEVEL`; reduce Compose to app plus pgvector PostgreSQL; remove Cairo, Celery, Redis, MinIO, OpenRouter, Kerykeion, S3, and unrelated dependencies.

- [ ] **Step 4: Replace test fixtures with persistence-safe fixtures**

Keep the test-database name guard. Before `Base.metadata.create_all`, run `CREATE EXTENSION IF NOT EXISTS vector`; skip integration tests when PostgreSQL or extension setup is unavailable. Do not drop or create schemas outside a database named `natalai_test` or ending in `_test` with `APP_ENV=test`.

- [ ] **Step 5: Run focused and full verification**

Run:

```bash
uv sync
uv run pytest -q
uv run python -m compileall -q app
uv run alembic upgrade head --sql > /tmp/natalai-upgrade.sql
docker compose config
git diff --check
```

Expected: unit tests pass, DB integration tests pass or explicitly skip when PostgreSQL is unavailable, compilation succeeds, migration SQL renders, Compose validates, and no whitespace errors are reported.

- [ ] **Step 6: Run live Alembic verification when test PostgreSQL is available**

Run:

```bash
APP_ENV=test DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/natalai_test uv run alembic upgrade head
APP_ENV=test DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/natalai_test uv run alembic downgrade base
APP_ENV=test DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/natalai_test uv run alembic upgrade head
```

Expected: all three commands exit zero. If the test database is unavailable, report this exact environmental limitation without weakening unit verification.

- [ ] **Step 7: Commit cleanup and documentation**

```bash
git add app tests README.md Dockerfile docker-compose.yml pyproject.toml uv.lock
git commit -m "refactor: remove legacy persistence surface"
```
