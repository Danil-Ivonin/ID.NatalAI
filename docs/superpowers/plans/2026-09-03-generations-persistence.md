# Generations Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add UUIDv7-backed CRUD for person-owned astro charts and neutral generations with strict result validation, S3 chart links, and consistent `GenerationNeutral` naming.

**Architecture:** Two focused domain packages define independent ORM and Pydantic models. Separate repositories perform SQLAlchemy operations, separate services enforce person ownership and transactions, and one `/generations` FastAPI router exposes both resources. The old `readings` package is removed atomically after every import moves.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy async ORM, PostgreSQL 18 UUIDv7/JSONB, Alembic, boto3-compatible S3, pytest.

**Spec:** `docs/superpowers/specs/2026-09-03-generations-persistence-design.md`

## Global Constraints

- Use `uuidv7()` as the PostgreSQL server default for both primary keys.
- `person_id` is required, immutable, and uses `ON DELETE CASCADE` for both resources.
- Store natal XML as `TEXT` and the permanent S3 object key in `astro_charts.chart_svg`.
- Store `token_usage` and validated `GenerationNeutralResult` documents as `JSONB`.
- Delete `NeutralChartReading`, `NeutralGeneration`, and the `app.domain.readings` compatibility surface; do not add aliases.
- Do not introduce a generic CRUD base class or new dependency.

---

### Task 1: Create Generation Domain Schemas and Remove Reading Names

**Files:**
- Create: `app/domain/generations/__init__.py`
- Create: `app/domain/generations/astro_charts/__init__.py`
- Create: `app/domain/generations/astro_charts/schemas.py`
- Create: `app/domain/generations/generation_neutral/__init__.py`
- Create: `app/domain/generations/generation_neutral/schemas.py`
- Delete: `app/domain/readings/__init__.py`
- Delete: `app/domain/readings/schemas.py`
- Test: `tests/test_generation_schemas.py`

**Interfaces:**
- Produces: `AstroChartCreate`, `AstroChartUpdate`, `AstroChartRead`.
- Produces: `GenerationNeutralCreate`, `GenerationNeutralUpdate`, `GenerationNeutralRead`, `GenerationNeutralResult`.
- `AstroChartRead.chart_svg` is a fresh URL; create/update `chart_svg` values are permanent object keys.

- [ ] **Step 1: Write failing strict-schema tests**

Create tests that validate the approved four-block document and reject a missing block, cross-block fact reference, duplicate fact ID, malformed XML, nullable required PATCH field, and missing `person_id`:

```python
def test_generation_neutral_result_requires_ordered_blocks():
    result = GenerationNeutralResult.model_validate(RESULT)
    assert [block.id.value for block in result.blocks] == [
        "general", "love", "work_money", "inner_demons"
    ]

def test_generation_neutral_result_rejects_missing_block():
    with pytest.raises(ValidationError):
        GenerationNeutralResult.model_validate({"blocks": RESULT["blocks"][:-1]})

def test_generation_create_requires_person():
    with pytest.raises(ValidationError):
        GenerationNeutralCreate.model_validate({
            "used_model": "model", "prompt": "prompt",
            "token_usage": {"total_tokens": 42}, "result": RESULT,
        })

def test_astro_chart_rejects_malformed_xml():
    with pytest.raises(ValidationError):
        AstroChartCreate(person_id=uuid4(), natal_xml="<broken", chart_svg="charts/a.svg")
```

- [ ] **Step 2: Run schema tests and verify RED**

Run: `uv run pytest tests/test_generation_schemas.py -q`

Expected: FAIL because `app.domain.generations` does not exist.

- [ ] **Step 3: Implement focused schemas**

Move the reusable evidence, fact, hook, and block validation logic from `readings/schemas.py` into `generation_neutral/schemas.py`. Replace the root type with:

```python
class GenerationNeutralResult(StrictModel):
    blocks: list[Block] = Field(min_length=4, max_length=4)

    @model_validator(mode="after")
    def validate_document(self) -> Self:
        expected = [BlockId.GENERAL, BlockId.LOVE, BlockId.WORK_MONEY, BlockId.INNER_DEMONS]
        if [block.id for block in self.blocks] != expected:
            raise ValueError("blocks must be ordered: general, love, work_money, inner_demons")
        fact_ids = [fact.id for block in self.blocks for fact in block.facts]
        hook_ids = [hook.id for block in self.blocks for hook in block.hooks]
        if len(fact_ids) != len(set(fact_ids)):
            raise ValueError("fact IDs must be unique")
        if len(hook_ids) != len(set(hook_ids)):
            raise ValueError("hook IDs must be unique")
        return self
```

Define CRUD schemas with required nonblank create fields and optional-but-non-null update fields. Keep `token_usage: dict[str, Any]`; type the result as `GenerationNeutralResult`. Validate `natal_xml` with `xml.etree.ElementTree.fromstring` in a Pydantic field validator so malformed documents produce `422` before persistence.

- [ ] **Step 4: Run schema tests and verify GREEN**

Run: `uv run pytest tests/test_generation_schemas.py -q`

Expected: PASS.

- [ ] **Step 5: Commit schema rename**

```bash
git add app/domain/generations app/domain/readings tests/test_generation_schemas.py
git commit -m "feat: define generation schemas"
```

---

### Task 2: Add ORM Models, Person Relationships, and Initial Migration

**Files:**
- Create: `app/domain/generations/astro_charts/models.py`
- Create: `app/domain/generations/generation_neutral/models.py`
- Modify: `app/domain/users/models.py`
- Modify: `app/db/models.py`
- Create: `app/db/migrations/versions/0001_users_and_generations.py`
- Delete: `app/domain/readings/models.py`
- Modify: `tests/test_database_models.py`
- Create: `tests/test_generation_models.py`

**Interfaces:**
- Produces ORM `AstroChart(id, person_id, natal_xml, chart_svg)` on table `astro_charts`.
- Produces ORM `GenerationNeutral(id, person_id, used_model, prompt, token_usage, result)` on table `generation_neutral`.
- Adds `Person.astro_charts` and `Person.generation_neutral` collections.

- [ ] **Step 1: Write failing metadata tests**

```python
def test_generation_models_require_person_and_uuid7():
    import app.db.models  # noqa: F401
    charts = Base.metadata.tables["astro_charts"]
    neutral = Base.metadata.tables["generation_neutral"]
    assert str(charts.c.id.server_default.arg) == "uuidv7()"
    assert str(neutral.c.id.server_default.arg) == "uuidv7()"
    assert next(iter(charts.c.person_id.foreign_keys)).ondelete == "CASCADE"
    assert next(iter(neutral.c.person_id.foreign_keys)).ondelete == "CASCADE"
    assert isinstance(neutral.c.result.type.dialect_impl(postgresql.dialect()), postgresql.JSONB)
    assert isinstance(neutral.c.token_usage.type.dialect_impl(postgresql.dialect()), postgresql.JSONB)
```

- [ ] **Step 2: Run metadata tests and verify RED**

Run: `uv run pytest tests/test_generation_models.py tests/test_database_models.py -q`

Expected: FAIL because the new tables are absent.

- [ ] **Step 3: Implement ORM models and relationships**

Use `Text`, PostgreSQL `UUID`/`JSONB`, and explicit indexed foreign keys. Example neutral model:

```python
class GenerationNeutral(Base):
    __tablename__ = "generation_neutral"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("persons.person_id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    used_model: Mapped[str] = mapped_column(Text, nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    token_usage: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    person: Mapped["Person"] = relationship(back_populates="generation_neutral")
```

Add child collections to `Person` with `cascade="all, delete-orphan"` and `passive_deletes=True`. Keep `Person.sex` consistent with the lowercase enum values by using `values_callable=lambda enum: [item.value for item in enum]` and `nullable=False`. Import both generation models from `app/db/models.py` and update its `__all__`.

- [ ] **Step 4: Create the initial migration**

Create revision `0001_users_and_generations` with `down_revision = None`. Create `sex_enum`, then `users`, `persons`, `astro_charts`, and `generation_neutral`; use `server_default=sa.text("uuidv7()")`, JSONB columns, required foreign keys, and person indexes. Downgrade drops child tables, persons, users, then `sex_enum`.

- [ ] **Step 5: Run model tests and verify GREEN**

Run: `uv run pytest tests/test_generation_models.py tests/test_database_models.py -q`

Expected: PASS.

- [ ] **Step 6: Commit persistence models**

```bash
git add app/domain/generations app/domain/readings app/domain/users/models.py app/db/models.py app/db/migrations/versions tests/test_generation_models.py tests/test_database_models.py
git commit -m "feat: persist person generations"
```

---

### Task 3: Implement Separate Repositories

**Files:**
- Create: `app/repositories/astro_chart_repository.py`
- Create: `app/repositories/generation_neutral_repository.py`
- Delete: `app/repositories/neutral_generation_repository.py`
- Modify: `app/repositories/user_repository.py`
- Modify: `app/repositories/__init__.py`
- Create: `tests/test_generation_repositories.py`
- Delete: `tests/test_neutral_generation_repository.py`

**Interfaces:**
- Produces identical CRUD method families: `create(data)`, `list_by_person(person_id)`, `get(id)`, `update(id, data)`, and `delete(id)`.
- Produces `UserRepository.get_person_by_id(person_id: UUID) -> Person | None` for ownership checks.

- [ ] **Step 1: Write failing repository lifecycle tests**

Use the existing lightweight fake-session pattern. For each repository assert create adds/flushed rows, list compiles a `person_id` filter, patch changes only provided fields, missing update returns `None`, and delete queues the matching row. Assert neutral create stores `result.model_dump(mode="json")` and `token_usage` as JSON-ready dictionaries.

- [ ] **Step 2: Run repository tests and verify RED**

Run: `uv run pytest tests/test_generation_repositories.py -q`

Expected: FAIL because the repositories do not exist.

- [ ] **Step 3: Implement minimal repository CRUD**

Use the established SQLAlchemy pattern:

```python
async def list_by_person(self, person_id: UUID) -> list[GenerationNeutral]:
    result = await self.session.execute(
        select(GenerationNeutral)
        .where(GenerationNeutral.person_id == person_id)
        .order_by(GenerationNeutral.id)
    )
    return list(result.scalars().all())

async def update(self, generation_id: UUID, data: GenerationNeutralUpdate):
    row = await self.get(generation_id)
    if row is None:
        return None
    values = data.model_dump(mode="json", exclude_unset=True)
    for field, value in values.items():
        setattr(row, field, value)
    await self.session.flush()
    return row
```

Serialize `GenerationNeutralResult` through Pydantic JSON mode before assigning JSONB. Do not commit in repositories.

- [ ] **Step 4: Run repository tests and verify GREEN**

Run: `uv run pytest tests/test_generation_repositories.py -q`

Expected: PASS.

- [ ] **Step 5: Commit repositories**

```bash
git add app/repositories tests/test_generation_repositories.py tests/test_neutral_generation_repository.py
git commit -m "feat: add generation repositories"
```

---

### Task 4: Implement Ownership and S3 Behavior in Services

**Files:**
- Create: `app/services/astro_chart_service.py`
- Create: `app/services/generation_neutral_service.py`
- Create: `tests/test_generation_services.py`

**Interfaces:**
- `AstroChartService(repository, user_repository, storage, commit)` returns `AstroChartRead` values with presigned `chart_svg` URLs.
- `GenerationNeutralService(repository, user_repository, commit)` returns `GenerationNeutralRead` values.
- Both services raise `NotFoundError("Person not found")` or their resource-specific message.

- [ ] **Step 1: Write failing service behavior tests**

Cover create/list rejecting a missing person without mutation, successful mutations committing exactly once, missing get/update/delete raising `NotFoundError`, immutable `person_id`, and chart reads calling `storage.presigned_url` with the stored key.

- [ ] **Step 2: Run service tests and verify RED**

Run: `uv run pytest tests/test_generation_services.py -q`

Expected: FAIL because the services do not exist.

- [ ] **Step 3: Implement service workflows**

Use one private ownership check per service and explicit result mapping:

```python
async def _require_person(self, person_id: UUID) -> None:
    if await self.user_repository.get_person_by_id(person_id) is None:
        raise NotFoundError("Person not found")

def _read(self, row: AstroChart) -> AstroChartRead:
    return AstroChartRead(
        id=row.id,
        person_id=row.person_id,
        natal_xml=row.natal_xml,
        chart_svg=self.storage.presigned_url(row.chart_svg),
    )
```

Commit only after create/update/delete succeeds. `GenerationNeutralService` maps ORM JSONB through `GenerationNeutralRead.model_validate(row)`.

- [ ] **Step 4: Run service tests and verify GREEN**

Run: `uv run pytest tests/test_generation_services.py -q`

Expected: PASS.

- [ ] **Step 5: Commit services**

```bash
git add app/services/astro_chart_service.py app/services/generation_neutral_service.py tests/test_generation_services.py
git commit -m "feat: add generation services"
```

---

### Task 5: Expose One Generations API Router

**Files:**
- Create: `app/api/v1/generations.py`
- Modify: `app/main.py`
- Create: `tests/test_generations_api.py`

**Interfaces:**
- Registers `router = APIRouter(prefix="/generations", tags=["generations"])`.
- Exposes ten approved CRUD routes.
- Requires `person_id: UUID` on both list handlers.

- [ ] **Step 1: Write failing HTTP contract tests**

Create an isolated FastAPI app with dependency overrides for both service factories. Exercise create/list/get/patch/delete for each resource. Verify create `201`, delete `204`, missing required list `person_id` returns `422`, and `NotFoundError` returns `404` through the application exception handler.

- [ ] **Step 2: Run API tests and verify RED**

Run: `uv run pytest tests/test_generations_api.py -q`

Expected: FAIL because `app.api.v1.generations` does not exist.

- [ ] **Step 3: Implement the router and dependencies**

Construct each service from the request-scoped session:

```python
def get_generation_neutral_service(
    session: AsyncSession = Depends(get_session),
) -> GenerationNeutralService:
    return GenerationNeutralService(
        GenerationNeutralRepository(session),
        UserRepository(session),
        session.commit,
    )
```

Construct `AstroChartService` with `ChartImageStorage(get_settings())`. Handlers only call services and return their typed schemas. Include the router once in `app/main.py` under `/api/v1`.

- [ ] **Step 4: Run API tests and verify GREEN**

Run: `uv run pytest tests/test_generations_api.py -q`

Expected: PASS.

- [ ] **Step 5: Commit API routes**

```bash
git add app/api/v1/generations.py app/main.py tests/test_generations_api.py
git commit -m "feat: expose generations CRUD API"
```

---

### Task 6: Remove Legacy Imports and Verify the Complete Change

**Files:**
- Verify: `app/domain/readings` was deleted in Tasks 1-2.
- Verify: `app/repositories/neutral_generation_repository.py` and `tests/test_neutral_generation_repository.py` were deleted in Task 3.
- Verify: `app/db/models.py` and `app/repositories/__init__.py` export only the new generation names.

**Interfaces:**
- Leaves zero imports or definitions using `app.domain.readings`, `NeutralChartReading`, `NeutralGeneration`, or `NeutralGenerationRepository`.
- Leaves the application importable with both `/api/v1/users` and `/api/v1/generations` routers.

- [ ] **Step 1: Verify legacy references were removed**

Run: `rg -n "app\.domain\.readings|NeutralChartReading|NeutralGenerationRepository|class NeutralGeneration" app tests`

Expected: no output.

- [ ] **Step 2: Run targeted tests**

Run: `uv run pytest tests/test_generation_schemas.py tests/test_generation_models.py tests/test_generation_repositories.py tests/test_generation_services.py tests/test_generations_api.py tests/test_users_crud.py tests/test_database_models.py -q`

Expected: PASS.

- [ ] **Step 3: Run structural verification**

Run: `uv run python -m compileall -q app`

Expected: exit 0.

Run: `git diff --check`

Expected: exit 0.

- [ ] **Step 4: Run the full available test suite**

Run: `uv run pytest -q`

Expected: all generation and user tests pass. If unrelated pre-existing tests still fail, record their exact names and output without changing unrelated behavior.
