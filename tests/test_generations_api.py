from datetime import UTC, date, datetime, time
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.domain.generation.enums import GenerationStatus


class FakePersonaRepository:
    personas = {}

    def __init__(self, session) -> None:
        self.session = session

    async def get(self, persona_id):
        return self.personas.get(persona_id)


class FakeGenerationRepository:
    generations = {}
    created_payloads = []
    status = GenerationStatus.PENDING

    def __init__(self, session) -> None:
        self.session = session

    async def create(self, payload):
        self.created_payloads.append(payload)
        generation = SimpleNamespace(
            id=uuid4(),
            person_name=payload.person_name,
            status=self.status,
            result_text=None,
            error_message=None,
            created_at=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
            completed_at=None,
        )
        self.generations[generation.id] = generation
        return generation

    async def get(self, generation_id):
        return self.generations.get(generation_id)


class FakeChartImageStorage:
    def __init__(self, settings) -> None:
        self.settings = settings

    def presigned_url(self, object_key):
        return f"https://storage.test/{object_key}?signature=test"


@pytest.fixture
def client(monkeypatch, generation_dispatch_spy, app_client):
    from app.api.v1 import generations

    FakePersonaRepository.personas = {}
    FakeGenerationRepository.generations = {}
    FakeGenerationRepository.created_payloads = []
    FakeGenerationRepository.status = GenerationStatus.PENDING

    monkeypatch.setattr(generations, "PersonaRepository", FakePersonaRepository)
    monkeypatch.setattr(generations, "GenerationRepository", FakeGenerationRepository)
    monkeypatch.setattr(generations, "ChartImageStorage", FakeChartImageStorage)
    app_client.dispatched_generation_ids = generation_dispatch_spy
    return app_client


def generation_payload(persona_id, person_name="Ada Lovelace"):
    return {
        "person_name": person_name,
        "gender": "female",
        "birth_date": date(1990, 1, 2).isoformat(),
        "birth_time": time(3, 4).isoformat(),
        "birth_place": {
            "lat": 55.7558,
            "lng": 37.6173,
            "timezone": "Europe/Moscow",
        },
        "persona_id": str(persona_id),
    }


def styled_report_payload() -> dict:
    section = {"title": "General", "text": "Readable section text."}
    return {
        "title": "Natal report",
        "intro": {"title": "Intro", "text": "Intro text."},
        "general": section,
        "love_and_sex": {"title": "Love", "text": "Love text."},
        "career_and_money": {"title": "Career", "text": "Career text."},
        "demons": {"title": "Demons", "text": "Demons text."},
        "final_summary": {"title": "Final", "text": "Final text."},
    }


def test_create_generation_with_person_name(client) -> None:
    persona_id = uuid4()
    FakePersonaRepository.personas[persona_id] = SimpleNamespace(
        id=persona_id,
    )

    response = client.post(
        "/api/v1/generations",
        json=generation_payload(persona_id, person_name="Ada Lovelace"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert body["generation_id"] == str(client.dispatched_generation_ids[0])
    assert client.fake_session.commits == 1
    assert FakeGenerationRepository.created_payloads[0].person_name == "Ada Lovelace"


def test_create_generation_without_person_name(client) -> None:
    persona_id = uuid4()
    FakePersonaRepository.personas[persona_id] = SimpleNamespace(
        id=persona_id,
    )
    payload = generation_payload(persona_id)
    payload.pop("person_name")

    response = client.post("/api/v1/generations", json=payload)

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "pending"
    assert FakeGenerationRepository.created_payloads[0].person_name is None
    assert client.dispatched_generation_ids == [
        next(iter(FakeGenerationRepository.generations))
    ]


def test_create_generation_accepts_string_status_from_database(client) -> None:
    persona_id = uuid4()
    FakePersonaRepository.personas[persona_id] = SimpleNamespace(
        id=persona_id,
    )
    FakeGenerationRepository.status = "pending"

    response = client.post("/api/v1/generations", json=generation_payload(persona_id))

    assert response.status_code == 201
    assert response.json()["status"] == "pending"


def test_create_generation_requires_persona_id(client) -> None:
    persona_id = uuid4()
    payload = generation_payload(persona_id)
    payload.pop("persona_id")

    response = client.post("/api/v1/generations", json=payload)

    assert response.status_code == 422
    assert FakeGenerationRepository.created_payloads == []
    assert client.dispatched_generation_ids == []


def test_create_generation_rejects_unknown_persona(client) -> None:
    persona_id = uuid4()

    response = client.post("/api/v1/generations", json=generation_payload(persona_id))

    assert response.status_code == 404
    assert response.json() == {"detail": "Persona not found"}
    assert FakeGenerationRepository.created_payloads == []
    assert client.dispatched_generation_ids == []


def test_get_generation(client) -> None:
    generation_id = uuid4()
    FakeGenerationRepository.generations[generation_id] = SimpleNamespace(
        id=generation_id,
        status=GenerationStatus.COMPLETED,
        result_json=styled_report_payload(),
        result_text="legacy plain text",
        chart_image_object_key=f"generations/{generation_id}/natal-chart.png",
        chart_image_mime_type="image/png",
        error_message=None,
        created_at=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
        completed_at=datetime(2026, 5, 17, 10, 1, tzinfo=UTC),
    )

    response = client.get(f"/api/v1/generations/{generation_id}")

    assert response.status_code == 200
    assert response.json() == {
        "generation_id": str(generation_id),
        "status": "completed",
        "result_text": styled_report_payload(),
        "chart_image": {
            "url": (
                "https://storage.test/"
                f"generations/{generation_id}/natal-chart.png?signature=test"
            ),
            "mime_type": "image/png",
        },
        "error_message": None,
        "created_at": "2026-05-17T10:00:00Z",
        "completed_at": "2026-05-17T10:01:00Z",
    }


def test_get_generation_accepts_string_status_from_database(client) -> None:
    generation_id = uuid4()
    FakeGenerationRepository.generations[generation_id] = SimpleNamespace(
        id=generation_id,
        status="completed",
        result_json=styled_report_payload(),
        result_text="legacy plain text",
        chart_image_object_key=None,
        chart_image_mime_type=None,
        error_message=None,
        created_at=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
        completed_at=datetime(2026, 5, 17, 10, 1, tzinfo=UTC),
    )

    response = client.get(f"/api/v1/generations/{generation_id}")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_get_generation_returns_null_chart_image_when_missing(client) -> None:
    generation_id = uuid4()
    FakeGenerationRepository.generations[generation_id] = SimpleNamespace(
        id=generation_id,
        status=GenerationStatus.COMPLETED,
        result_json=styled_report_payload(),
        result_text="legacy plain text",
        chart_image_object_key=None,
        chart_image_mime_type=None,
        error_message=None,
        created_at=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
        completed_at=datetime(2026, 5, 17, 10, 1, tzinfo=UTC),
    )

    response = client.get(f"/api/v1/generations/{generation_id}")

    assert response.status_code == 200
    assert response.json()["chart_image"] is None
