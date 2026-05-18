from inspect import getsource, iscoroutinefunction
from types import SimpleNamespace
from uuid import uuid4


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
