# Required Persona Selection Design

## Goal

Every generation request must explicitly include an existing `persona_id`. The project no longer has bootstrap, default, preselected, or status-gated personas.

## API Behavior

`POST /api/v1/generations` keeps `persona_id` as a required UUID field. If the client omits it, FastAPI returns `422 Unprocessable Entity`. If the UUID is valid but no persona exists with that id, the endpoint returns `404 Not Found` with `{"detail": "Persona not found"}`.

Persona endpoints no longer expose or accept a status flag. `GET /api/v1/personas` returns all personas.

## Data Model

The persona status column is removed. Repository methods use existence checks only. `generations.persona_id` remains non-null and keeps its foreign key to `personas.id`.

Because the project has not been deployed, Alembic history is collapsed into one initial migration that includes all current tables and chart image fields.

## Seed Removal

The bootstrap module and bundled persona data are removed. Startup docs no longer instruct users to preload data. Prompt templates are managed through the prompt template API instead of startup preload flow.

## Testing

Tests cover generation success with an existing persona, `422` for missing `persona_id`, and `404 Persona not found` for unknown persona. Schema, repository, docs, and domain model tests are updated so legacy persona status and bundled persona data no longer appear as required project behavior.
