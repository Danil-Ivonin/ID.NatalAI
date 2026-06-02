# Backend API Contracts

Документ описывает публичный HTTP API текущего FastAPI backend. Базовый префикс всех ручек: `/api/v1`.

## Общие правила

- Формат обмена: JSON.
- Даты: ISO 8601.
- `UUID`: строка в формате UUID v4.
- Аутентификация: в текущей реализации отсутствует.
- Пагинация: в текущей реализации отсутствует, списковые ручки возвращают массив целиком.
- Ошибка валидации FastAPI: `422 Unprocessable Entity` со стандартным телом `{"detail": [...]}`.
- Ошибки приложения возвращаются в формате FastAPI `HTTPException`: `{"detail": "message"}`.

## Enums

```json
{
  "Gender": ["male", "female"],
  "GenerationStatus": ["pending", "processing", "completed", "failed"],
  "PromptTemplateType": [
    "astrology_profile_extraction",
    "styled_report_generation"
  ]
}
```

## Shared Schemas

### `BirthPlace`

```json
{
  "city": "Moscow",
  "country": "Russia",
  "lat": 55.7558,
  "lng": 37.6173,
  "timezone": "Europe/Moscow"
}
```

### `ReportSection`

```json
{
  "title": "General",
  "text": "Readable section text."
}
```

### `StyledNatalReport`

```json
{
  "title": "Natal report",
  "intro": { "title": "Intro", "text": "Intro text." },
  "general": { "title": "General", "text": "General text." },
  "love_and_sex": { "title": "Love", "text": "Love text." },
  "career_and_money": { "title": "Career", "text": "Career text." },
  "demons": { "title": "Demons", "text": "Demons text." },
  "final_summary": { "title": "Final", "text": "Final text." }
}
```

## Generations

### Create Generation

`POST /api/v1/generations`

Создает запись генерации со статусом `pending`, проверяет, что персона существует и активна, затем отправляет background job в Celery.

Request body:

```json
{
  "person_name": "Ada Lovelace",
  "gender": "female",
  "birth_date": "1990-01-02",
  "birth_time": "03:04:00",
  "birth_place": {
    "city": "Moscow",
    "country": "Russia",
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
- `birth_date`: `date`, required, example `1990-01-02`.
- `birth_time`: `time`, required, example `03:04:00`.
- `birth_place`: `BirthPlace`, required.
- `persona_id`: `UUID`, required. Persona must exist and be active.

Success response: `201 Created`

```json
{
  "generation_id": "11111111-1111-4111-8111-111111111111",
  "status": "pending"
}
```

Errors:

- `404 Not Found`: `{"detail": "Active persona not found"}`
- `422 Unprocessable Entity`: invalid body, invalid UUID, invalid enum, invalid date/time.

### Get Generation

`GET /api/v1/generations/{generation_id}`

Возвращает статус генерации, итоговый отчет, ссылку на изображение натальной карты и ошибку, если job завершилась неуспешно.

Path params:

- `generation_id`: `UUID`, required.

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

Nullable response fields:

- `result_text`: `StyledNatalReport | null`. Usually `null` while status is `pending`, `processing`, or `failed`.
- `chart_image`: `{ "url": string, "mime_type": string } | null`.
- `error_message`: `string | null`. Usually filled when status is `failed`.
- `completed_at`: `datetime | null`.

Errors:

- `404 Not Found`: `{"detail": "Generation not found"}`
- `422 Unprocessable Entity`: invalid `generation_id`.

## Personas

### Persona Nested Schemas

`PersonaStyleProfileCreate`

```json
{
  "voice_description": "Direct sarcastic voice.",
  "humor_style": "Dry roast humor.",
  "speech_patterns": ["short punchlines", "rhetorical questions"],
  "forbidden_rules": ["Do not use hate speech."],
  "allowed_rules": ["Use sharp jokes about behavior patterns."]
}
```

`PersonaQuoteCreate`

```json
{
  "text": "Example quote.",
  "usage_context": "intro",
  "is_allowed": true
}
```

`PersonaPhraseTemplateCreate`

```json
{
  "type": "transition",
  "template": "And here is the part where {topic} gets messy.",
  "usage": "section transition"
}
```

`PersonaStyleExampleCreate`

```json
{
  "title": "Example",
  "text": "Sample style paragraph.",
  "tags": ["roast", "direct"]
}
```

Read variants of nested schemas include `id`, `persona_id`, `created_at`, and `updated_at`.

### Create Persona

`POST /api/v1/personas`

Создает персону вместе с вложенными style profile, quotes, phrase templates и style examples.

Request body:

```json
{
  "name": "Roast Persona",
  "slug": "roast-persona",
  "description": "Sharp report style.",
  "is_active": true,
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

Fields:

- `name`: `string`, required.
- `slug`: `string`, required, unique at DB level.
- `description`: `string | null`, optional.
- `is_active`: `boolean`, optional, default `true`.
- `style_profile`: `PersonaStyleProfileCreate | null`, optional.
- `quotes`: `PersonaQuoteCreate[]`, optional, default `[]`.
- `phrase_templates`: `PersonaPhraseTemplateCreate[]`, optional, default `[]`.
- `style_examples`: `PersonaStyleExampleCreate[]`, optional, default `[]`.

Success response: `201 Created`

```json
{
  "id": "22222222-2222-4222-8222-222222222222",
  "name": "Roast Persona",
  "slug": "roast-persona",
  "description": "Sharp report style.",
  "is_active": true,
  "created_at": "2026-05-17T10:00:00Z",
  "updated_at": "2026-05-17T10:00:00Z",
  "style_profile": null,
  "quotes": [],
  "phrase_templates": [],
  "style_examples": []
}
```

Errors:

- `422 Unprocessable Entity`: invalid body.

### List Personas

`GET /api/v1/personas`

Success response: `200 OK`

```json
[
  {
    "id": "22222222-2222-4222-8222-222222222222",
    "name": "Roast Persona",
    "slug": "roast-persona",
    "description": "Sharp report style.",
    "is_active": true,
    "created_at": "2026-05-17T10:00:00Z",
    "updated_at": "2026-05-17T10:00:00Z",
    "style_profile": null,
    "quotes": [],
    "phrase_templates": [],
    "style_examples": []
  }
]
```

### Get Persona

`GET /api/v1/personas/{persona_id}`

Path params:

- `persona_id`: `UUID`, required.

Success response: `200 OK`, body is `PersonaRead`.

Errors:

- `404 Not Found`: `{"detail": "Persona not found"}`
- `422 Unprocessable Entity`: invalid `persona_id`.

### Update Persona

`PATCH /api/v1/personas/{persona_id}`

Частично обновляет верхнеуровневые поля персоны и ее `style_profile`. В текущем контракте вложенные `quotes`, `phrase_templates`, `style_examples` через `PATCH` не обновляются.

Path params:

- `persona_id`: `UUID`, required.

Request body:

```json
{
  "name": "Updated Persona",
  "description": "Updated description.",
  "is_active": false,
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
- `is_active`: `boolean | null`.
- `style_profile`: partial object with optional `voice_description`, `humor_style`, `speech_patterns`, `forbidden_rules`, `allowed_rules`.

Success response: `200 OK`, body is `PersonaRead`.

Errors:

- `404 Not Found`: `{"detail": "Persona not found"}`
- `422 Unprocessable Entity`: invalid path or body.

## Prompt Templates

### Create Prompt Template

`POST /api/v1/prompt-templates`

Создает prompt template. Если `is_active=true`, backend деактивирует другие активные шаблоны того же `type`.

Request body:

```json
{
  "name": "Report prompt v1",
  "type": "styled_report_generation",
  "version": 1,
  "content": "System prompt text...",
  "is_active": true,
  "metadata": {
    "owner": "backend"
  }
}
```

Fields:

- `name`: `string`, required.
- `type`: `PromptTemplateType`, required.
- `version`: `integer`, required.
- `content`: `string`, required.
- `is_active`: `boolean`, optional, default `true`.
- `metadata`: `object`, optional, default `{}`. Request also accepts internal alias `template_metadata`.

Success response: `201 Created`

```json
{
  "name": "Report prompt v1",
  "type": "styled_report_generation",
  "version": 1,
  "content": "System prompt text...",
  "is_active": true,
  "metadata": {
    "owner": "backend"
  },
  "id": "33333333-3333-4333-8333-333333333333",
  "created_at": "2026-05-17T10:00:00Z",
  "updated_at": "2026-05-17T10:00:00Z"
}
```

Errors:

- `422 Unprocessable Entity`: invalid body.

### List Prompt Templates

`GET /api/v1/prompt-templates`

Optional query params:

- `type`: `PromptTemplateType`. If omitted, returns all prompt templates.

Success response: `200 OK`

```json
[
  {
    "name": "Report prompt v1",
    "type": "styled_report_generation",
    "version": 1,
    "content": "System prompt text...",
    "is_active": true,
    "metadata": {},
    "id": "33333333-3333-4333-8333-333333333333",
    "created_at": "2026-05-17T10:00:00Z",
    "updated_at": "2026-05-17T10:00:00Z"
  }
]
```

Errors:

- `422 Unprocessable Entity`: invalid `type`.

### Get Active Prompt Template

`GET /api/v1/prompt-templates/active?type={type}`

Query params:

- `type`: `PromptTemplateType`, required.

Success response: `200 OK`, body is `PromptTemplateRead`.

Errors:

- `404 Not Found`: `{"detail": "Active prompt template not found"}`
- `422 Unprocessable Entity`: missing or invalid `type`.

### Activate Prompt Template

`POST /api/v1/prompt-templates/{template_id}/activate`

Активирует шаблон и деактивирует остальные активные шаблоны того же `type`.

Path params:

- `template_id`: `UUID`, required.

Success response: `200 OK`

```json
{
  "name": "Report prompt v1",
  "type": "styled_report_generation",
  "version": 1,
  "content": "System prompt text...",
  "is_active": true,
  "metadata": {},
  "prompt_template_id": "33333333-3333-4333-8333-333333333333",
  "created_at": "2026-05-17T10:00:00Z",
  "updated_at": "2026-05-17T10:00:00Z"
}
```

Errors:

- `404 Not Found`: `{"detail": "Prompt template not found"}`
- `422 Unprocessable Entity`: invalid `template_id`.
