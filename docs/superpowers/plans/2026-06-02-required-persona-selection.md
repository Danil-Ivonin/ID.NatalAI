# Required Persona Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Require explicit existing persona selection for each generation and remove status-gated, default, and bundled persona logic.

**Architecture:** Keep the existing FastAPI, Pydantic, repository, and SQLAlchemy boundaries. Replace status-gated persona lookup with plain persona lookup and remove the legacy status flag from schemas, models, migrations, tests, and docs.

**Tech Stack:** Python 3.11, FastAPI, Pydantic, SQLAlchemy async ORM, Alembic, pytest.

---

### Task 1: Remove Status-Gated Persona API Behavior

**Files:**
- Modify: `app/api/v1/generations.py`
- Modify: `app/repositories/persona_repository.py`
- Modify: `app/services/persona_context_service.py`
- Test: `tests/test_generations_api.py`
- Test: `tests/test_repositories.py`
- Test: `tests/test_generation_pipeline.py`

- [ ] Update generation creation to call `PersonaRepository.get(payload.persona_id)`.
- [ ] Return `404` with `Persona not found` when lookup returns `None`.
- [ ] Remove status-gated filters from persona context lookup.
- [ ] Update tests to use `get` and expect missing-persona behavior.

### Task 2: Remove Persona Status Flag From Persona Domain

**Files:**
- Modify: `app/domain/persona/models.py`
- Modify: `app/domain/persona/schemas.py`
- Modify: `app/db/migrations/versions/0001_initial_schema.py`
- Delete: `app/db/migrations/versions/0002_chart_image.py`
- Test: `tests/test_schemas.py`
- Test: `tests/test_domain_models.py`
- Test: `tests/test_repositories.py`

- [ ] Delete the status flag from SQLAlchemy persona model.
- [ ] Delete the status flag from Pydantic create, update, and read schemas.
- [ ] Remove the status flag from migration table creation.
- [ ] Move chart image columns into `0001_initial_schema.py`.
- [ ] Delete the second chart image migration.

### Task 3: Delete Seed Flow

**Files:**
- Delete the bootstrap preload module.
- Delete its tests.
- Modify: `README.md`
- Modify: `docs/api-contracts.md`

- [ ] Delete bootstrap module and its tests.
- [ ] Remove startup commands that preload bundled data.
- [ ] Remove bundled-persona and status-gated wording from docs.
- [ ] Keep prompt template API documented as the way to create prompt templates.

### Task 4: Verify

**Files:**
- Run tests across changed behavior.

- [ ] Run targeted pytest for API, schema, repository, domain, generation pipeline.
- [ ] Run full pytest suite.
- [ ] Run `rg` scans for removed legacy persona concepts.
