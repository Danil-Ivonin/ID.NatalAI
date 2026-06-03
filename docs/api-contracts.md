# Backend API Contracts

Base prefix: `/api/v1`.

## General Rules

- Format: JSON.
- Dates and datetimes: ISO 8601.
- UUID fields use UUID string format.
- Authentication is not implemented in the current backend.
- List endpoints currently return full arrays without pagination.
- FastAPI validation errors return `422 Unprocessable Entity` with the standard `{"detail": [...]}` body.

## Generations

### Create Generation

`POST /api/v1/generations`

Creates a generation record with `pending` status, verifies that the submitted `persona_id` exists, then dispatches a Celery background job.

Request body:

```json
{
  "person_name": "Ada Lovelace",
  "gender": "female",
  "birth_date": "1990-01-02",
  "birth_time": "03:04:00",
  "birth_place": {
    "lat": 55.7558,
    "lng": 37.6173,
    "timezone": "Europe/Moscow"
  },
  "persona_id": "00000000-0000-4000-8000-000000000000"
}
```

Fields:

- `person_name`: `string | null`, optional.
- `gender`: `"male" | "female" | null`, optional.
- `birth_date`: `date`, required.
- `birth_time`: `time`, required.
- `birth_place`: `BirthPlace`, required.
- `persona_id`: `UUID`, required. Persona must exist.

Success response: `201 Created`

```json
{
  "generation_id": "11111111-1111-4111-8111-111111111111",
  "status": "pending"
}
```

Errors:

- `404 Not Found`: `{"detail": "Persona not found"}`
- `422 Unprocessable Entity`: invalid body, missing `persona_id`, invalid UUID, invalid enum, invalid date/time.

### Get Generation

`GET /api/v1/generations/{generation_id}`

Returns generation status, final report, natal chart image URL, and failure details when present.

Success response: `200 OK`

```json
{
  "generation_id": "11111111-1111-4111-8111-111111111111",
  "status": "completed",
  "result_text": {
    "title": "Natal report",
    "intro": { "title": "Intro", "text": "Intro text." },
    "general": { "title": "General", "text": "General text." },
    "love_and_sex": { "title": "Love", "text": "Love text." },
    "career_and_money": { "title": "Career", "text": "Career text." },
    "demons": { "title": "Demons", "text": "Demons text." },
    "final_summary": { "title": "Final", "text": "Final text." }
  },
  "chart_image": {
    "url": "https://storage.example/generations/id/natal-chart.svg?signature=...",
    "mime_type": "image/svg+xml"
  },
  "error_message": null,
  "created_at": "2026-05-17T10:00:00Z",
  "completed_at": "2026-05-17T10:01:00Z"
}
```

Errors:

- `404 Not Found`: `{"detail": "Generation not found"}`
- `422 Unprocessable Entity`: invalid `generation_id`.

## Personas

### Create Persona

`POST /api/v1/personas`

Creates a persona with optional nested style profile, quotes, phrase templates, and style examples.

Request body:

```json
{
  "name": "Roast Persona",
  "slug": "roast-persona",
  "description": "Sharp report style.",
  "style_profile": {
    "voice_description": "Direct sarcastic voice.",
    "humor_style": "Dry roast humor.",
    "speech_patterns": ["short punchlines"],
    "forbidden_rules": ["Do not use hate speech."],
    "allowed_rules": ["Use sharp jokes about behavior patterns."]
  },
  "quotes": [],
  "phrase_templates": [],
  "style_examples": []
}
```

Success response: `201 Created`, body is `PersonaRead`.

### List Personas

`GET /api/v1/personas`

Returns all personas.

### Get Persona

`GET /api/v1/personas/{persona_id}`

Errors:

- `404 Not Found`: `{"detail": "Persona not found"}`
- `422 Unprocessable Entity`: invalid `persona_id`.

### Update Persona

`PATCH /api/v1/personas/{persona_id}`

Partially updates top-level persona fields and `style_profile`.

Request body:

```json
{
  "name": "Updated Persona",
  "description": "Updated description.",
  "style_profile": {
    "humor_style": "More deadpan.",
    "allowed_rules": ["Keep jokes focused on chart patterns."]
  }
}
```

All fields are optional:

- `name`: `string | null`.
- `slug`: `string | null`.
- `description`: `string | null`.
- `style_profile`: partial object with optional `voice_description`, `humor_style`, `speech_patterns`, `forbidden_rules`, `allowed_rules`.

Errors:

- `404 Not Found`: `{"detail": "Persona not found"}`
- `422 Unprocessable Entity`: invalid path or body.

## Prompt Templates

Prompt templates are managed through `/api/v1/prompt-templates`. Generation requires one current template for `astrology_profile_extraction` and one current template for `styled_report_generation`.
