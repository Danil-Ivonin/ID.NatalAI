from uuid import uuid4


def test_generate_free_task_forwards_ids_to_async_worker(monkeypatch) -> None:
    from app.workers import tasks

    person_id = uuid4()
    character_id = uuid4()
    received = {}

    def run(function, *args):
        received["function"] = function
        received["args"] = args

    monkeypatch.setattr(tasks.anyio, "run", run)
    tasks.generate_free.run(str(person_id), str(character_id))

    assert received == {
        "function": tasks._run_free_generation,
        "args": (tasks.generate_free, person_id, character_id),
    }
    assert tasks.generate_free.name == "generate_free"
