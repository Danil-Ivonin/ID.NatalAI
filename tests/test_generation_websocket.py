from types import SimpleNamespace
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_free_generation_websocket_streams_completed_stages_and_result(monkeypatch) -> None:
    from app.api.v1 import generations

    person_id = uuid4()
    character_id = uuid4()
    generation_id = uuid4()
    task = SimpleNamespace(id="task-id")
    snapshots = iter(
        [
            ("PENDING", None),
            (
                "PROGRESS",
                {
                    "completed_stages": [
                        {"stage": "generation_created", "generation_id": str(generation_id)},
                        {"stage": "astro_chart_created", "generation_id": str(generation_id)},
                    ]
                },
            ),
            (
                "SUCCESS",
                {
                    "completed_stages": [
                        {"stage": "generation_created", "generation_id": str(generation_id)},
                        {"stage": "astro_chart_created", "generation_id": str(generation_id)},
                        {"stage": "general_generated", "generation_id": str(generation_id)},
                    ],
                    "generation_id": str(generation_id),
                    "chart_url": "https://s3.test/chart.svg",
                    "blocks": {
                        "intro": {"title": "Вступление", "text": "Привет."},
                        "general": {"title": "Общее", "text": "Текст."},
                    },
                },
            ),
        ]
    )

    monkeypatch.setattr(generations, "dispatch_free_generation", lambda *_: task)

    async def snapshot(_task):
        return next(snapshots)

    monkeypatch.setattr(generations, "task_snapshot", snapshot)
    app = FastAPI()
    app.include_router(generations.router, prefix="/api/v1")

    with TestClient(app).websocket_connect("/api/v1/generations/free") as websocket:
        websocket.send_json(
            {"person_id": str(person_id), "character_id": str(character_id)}
        )
        messages = [websocket.receive_json() for _ in range(5)]

    assert messages == [
        {"type": "accepted", "task_id": "task-id"},
        {
            "type": "stage_completed",
            "stage": "generation_created",
            "generation_id": str(generation_id),
        },
        {
            "type": "stage_completed",
            "stage": "astro_chart_created",
            "generation_id": str(generation_id),
        },
        {
            "type": "stage_completed",
            "stage": "general_generated",
            "generation_id": str(generation_id),
        },
        {
            "type": "completed",
            "generation_id": str(generation_id),
            "chart_url": "https://s3.test/chart.svg",
            "blocks": {
                "intro": {"title": "Вступление", "text": "Привет."},
                "general": {"title": "Общее", "text": "Текст."},
            },
        },
    ]


def test_free_generation_websocket_returns_task_failure(monkeypatch) -> None:
    from app.api.v1 import generations

    task = SimpleNamespace(id="task-id")
    monkeypatch.setattr(generations, "dispatch_free_generation", lambda *_: task)

    async def snapshot(_task):
        return "FAILURE", RuntimeError("OpenRouter unavailable")

    monkeypatch.setattr(generations, "task_snapshot", snapshot)
    app = FastAPI()
    app.include_router(generations.router, prefix="/api/v1")

    with TestClient(app).websocket_connect("/api/v1/generations/free") as websocket:
        websocket.send_json(
            {"person_id": str(uuid4()), "character_id": str(uuid4())}
        )
        assert websocket.receive_json() == {"type": "accepted", "task_id": "task-id"}
        assert websocket.receive_json() == {
            "type": "failed",
            "error": "OpenRouter unavailable",
        }
