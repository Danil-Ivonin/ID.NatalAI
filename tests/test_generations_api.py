from datetime import UTC, date, datetime, time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.database import get_session
from app.domain.generation.enums import GenerationStatus


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class FakePersonaRepository:
    active_personas = {}

    def __init__(self, session) -> None:
        self.session = session

    async def get_active(self, persona_id):
        return self.active_personas.get(persona_id)


class FakeGenerationRepository:
    generations = {}
    created_payloads = []

    def __init__(self, session) -> None:
        self.session = session

    async def create(self, payload):
        self.created_payloads.append(payload)
        generation = SimpleNamespace(
            id=uuid4(),
            person_name=payload.person_name,
            status=GenerationStatus.PENDING,
            result_text=None,
            error_message=None,
            created_at=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
            completed_at=None,
        )
        self.generations[generation.id] = generation
        return generation

    async def get(self, generation_id):
        return self.generations.get(generation_id)


@pytest.fixture
def client(monkeypatch):
    from app.api.v1 import generations
    from app.main import app

    session = FakeSession()
    dispatched = []
    FakePersonaRepository.active_personas = {}
    FakeGenerationRepository.generations = {}
    FakeGenerationRepository.created_payloads = []

    async def override_get_session():
        yield session

    app.dependency_overrides[get_session] = override_get_session
    monkeypatch.setattr(generations, "PersonaRepository", FakePersonaRepository)
    monkeypatch.setattr(generations, "GenerationRepository", FakeGenerationRepository)
    monkeypatch.setattr(generations, "dispatch_generation_job", dispatched.append)

    with TestClient(app) as test_client:
        test_client.fake_session = session
        test_client.dispatched_generation_ids = dispatched
        yield test_client

    app.dependency_overrides.clear()


def generation_payload(persona_id, person_name="Ada Lovelace"):
    return {
        "person_name": person_name,
        "gender": "female",
        "birth_date": date(1990, 1, 2).isoformat(),
        "birth_time": time(3, 4).isoformat(),
        "birth_place": {
            "city": "Moscow",
            "country": "Russia",
            "lat": 55.7558,
            "lng": 37.6173,
            "timezone": "Europe/Moscow",
        },
        "persona_id": str(persona_id),
    }


def test_create_generation_with_person_name(client) -> None:
    persona_id = uuid4()
    FakePersonaRepository.active_personas[persona_id] = SimpleNamespace(
        id=persona_id,
        is_active=True,
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
    FakePersonaRepository.active_personas[persona_id] = SimpleNamespace(
        id=persona_id,
        is_active=True,
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


def test_get_generation(client) -> None:
    generation_id = uuid4()
    FakeGenerationRepository.generations[generation_id] = SimpleNamespace(
        id=generation_id,
        status=GenerationStatus.COMPLETED,
        result_text="Natal report",
        error_message=None,
        created_at=datetime(2026, 5, 17, 10, 0, tzinfo=UTC),
        completed_at=datetime(2026, 5, 17, 10, 1, tzinfo=UTC),
    )

    response = client.get(f"/api/v1/generations/{generation_id}")

    assert response.status_code == 200
    assert response.json() == {
        "generation_id": str(generation_id),
        "status": "completed",
        "result_text": "Natal report",
        "error_message": None,
        "created_at": "2026-05-17T10:00:00Z",
        "completed_at": "2026-05-17T10:01:00Z",
    }
