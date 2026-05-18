from inspect import getsource, iscoroutinefunction
from types import SimpleNamespace
from uuid import uuid4

import pytest


def test_generate_natal_report_task_is_sync_function() -> None:
    from app.workers.tasks import generate_natal_report_task

    assert not iscoroutinefunction(generate_natal_report_task.run)


def test_dispatch_generation_job_delays_worker_task(monkeypatch) -> None:
    from app.api.v1.generations import dispatch_generation_job
    from app.workers import tasks

    generation_id = uuid4()
    delayed = []
    monkeypatch.setattr(
        tasks,
        "generate_natal_report_task",
        SimpleNamespace(delay=delayed.append),
    )

    dispatch_generation_job(generation_id)

    assert delayed == [str(generation_id)]


def test_dispatch_generation_job_does_not_suppress_import_errors() -> None:
    from app.api.v1.generations import dispatch_generation_job

    assert "except ModuleNotFoundError" not in getsource(dispatch_generation_job)


def test_celery_app_imports_worker_task() -> None:
    from app.core.celery_app import celery_app

    assert "generate_natal_report_task" in celery_app.tasks


@pytest.mark.asyncio
async def test_run_generation_injects_transaction_callbacks(monkeypatch) -> None:
    from app.workers import tasks

    events = []

    class FakeSession:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

        async def commit(self):
            events.append("commit")

        async def rollback(self):
            events.append("rollback")

    class FakeOpenRouterClient:
        def __init__(self, settings):
            self.settings = settings

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, traceback):
            return None

    class FakeAIGenerationService:
        def __init__(self, **kwargs):
            self.commit = kwargs["commit"]
            self.rollback = kwargs["rollback"]
            events.append("callbacks")

        async def generate(self, generation_id):
            await self.commit()
            await self.rollback()

    monkeypatch.setattr(tasks, "get_settings", lambda: object())
    monkeypatch.setattr(tasks, "async_session_factory", lambda: FakeSession())
    monkeypatch.setattr(tasks, "GenerationRepository", lambda session: object())
    monkeypatch.setattr(tasks, "PromptTemplateRepository", lambda session: object())
    monkeypatch.setattr(tasks, "PersonaRepository", lambda session: object())
    monkeypatch.setattr(tasks, "OpenRouterClient", FakeOpenRouterClient)
    monkeypatch.setattr(tasks, "AIGenerationService", FakeAIGenerationService)

    await tasks._run_generation(str(uuid4()))

    assert events == ["callbacks", "commit", "rollback"]
