from datetime import date, time
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import Enum
from sqlalchemy.dialects import postgresql

from app.core.database import Base


class ScalarResult:
    def __init__(self, values) -> None:
        self.values = values

    def all(self):
        return self.values


class ExecuteResult:
    def __init__(self, values) -> None:
        self.values = values

    def scalars(self):
        return ScalarResult(self.values)

    def scalar_one_or_none(self):
        return self.values[0] if self.values else None


class FakeSession:
    def __init__(self, *, get_result=None, execute_results=()) -> None:
        self.get_result = get_result
        self.execute_results = list(execute_results)
        self.added = []
        self.deleted = []
        self.flushed = 0

    def add(self, row) -> None:
        if hasattr(row, "user_id") and row.user_id is None:
            row.user_id = uuid4()
        if hasattr(row, "person_id") and row.person_id is None:
            row.person_id = uuid4()
        self.added.append(row)

    async def get(self, model, row_id):
        return self.get_result

    async def execute(self, statement):
        return ExecuteResult(self.execute_results.pop(0))

    async def flush(self) -> None:
        self.flushed += 1

    async def delete(self, row) -> None:
        self.deleted.append(row)


def person_payload() -> dict:
    return {
        "name": "Анна",
        "sex": "female",
        "birth_date": date(1990, 1, 2),
        "birth_time": time(3, 4),
        "birth_lat": 55.75,
        "birth_lng": 37.62,
        "birth_timezone": "Europe/Moscow",
        "birth_city": "Москва",
        "birth_nation": "RU",
    }


class CommitSession:
    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1


class MemoryUserRepository:
    users = {}
    persons = {}

    def __init__(self, session) -> None:
        pass

    async def create_user(self, data):
        user = SimpleNamespace(user_id=uuid4(), confirmed=False, **data.model_dump())
        self.users[user.user_id] = user
        return user

    async def list_users(self):
        return list(self.users.values())

    async def get_user(self, user_id):
        return self.users.get(user_id)

    async def update_user(self, user_id, data):
        user = self.users.get(user_id)
        if user is not None:
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(user, field, value)
        return user

    async def delete_user(self, user_id):
        if user_id not in self.users:
            return False
        del self.users[user_id]
        return True

    async def create_person(self, user_id, data):
        person = SimpleNamespace(
            person_id=uuid4(), user_id=user_id, **data.model_dump()
        )
        self.persons[(user_id, person.person_id)] = person
        return person

    async def list_persons(self, user_id):
        return [person for (owner_id, _), person in self.persons.items() if owner_id == user_id]

    async def get_person(self, user_id, person_id):
        return self.persons.get((user_id, person_id))

    async def update_person(self, user_id, person_id, data):
        person = await self.get_person(user_id, person_id)
        if person is not None:
            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(person, field, value)
        return person

    async def delete_person(self, user_id, person_id):
        return self.persons.pop((user_id, person_id), None) is not None


def users_client(monkeypatch) -> TestClient:
    from app.api.v1 import users as users_api
    from app.core.database import get_session
    from app.core.exceptions import NotFoundError
    from app.main import not_found_handler

    MemoryUserRepository.users = {}
    MemoryUserRepository.persons = {}
    monkeypatch.setattr(users_api, "UserRepository", MemoryUserRepository)
    app = FastAPI()
    app.include_router(users_api.router, prefix="/api/v1")
    app.add_exception_handler(NotFoundError, not_found_handler)
    app.dependency_overrides[get_session] = lambda: CommitSession()
    return TestClient(app)


def test_user_models_use_database_uuid7_and_cascading_person_owner() -> None:
    import app.domain.users.models  # noqa: F401

    users = Base.metadata.tables["users"]
    persons = Base.metadata.tables["persons"]

    assert str(users.c.user_id.server_default.arg) == "uuidv7()"
    assert str(persons.c.person_id.server_default.arg) == "uuidv7()"
    assert next(iter(persons.c.user_id.foreign_keys)).ondelete == "CASCADE"
    assert isinstance(persons.c.sex.type.dialect_impl(postgresql.dialect()), Enum)


def test_user_and_person_schemas_support_reads_and_partial_updates() -> None:
    from app.domain.users.schemas import (
        PersonCreate,
        PersonRead,
        PersonUpdate,
        UserRead,
        UserUpdate,
    )

    user_id = uuid4()
    person_id = uuid4()
    person_data = person_payload()

    assert UserRead(user_id=user_id, email="a@example.com", confirmed=False).user_id == user_id
    assert UserUpdate(confirmed=True).model_dump(exclude_unset=True) == {"confirmed": True}
    assert PersonCreate(**person_data).sex.value == "female"
    assert PersonUpdate(name="Аня").model_dump(exclude_unset=True) == {"name": "Аня"}
    assert PersonRead(person_id=person_id, user_id=user_id, **person_data).person_id == person_id


def test_person_schema_rejects_invalid_coordinates() -> None:
    from app.domain.users.schemas import PersonCreate, PersonUpdate, UserUpdate

    with pytest.raises(ValidationError):
        PersonCreate(
            name="Анна",
            birth_date=date(1990, 1, 2),
            birth_time=time(3, 4),
            birth_lat=91,
            birth_lng=37.62,
            birth_timezone="Europe/Moscow",
            birth_city="Москва",
            birth_nation="RU",
        )
    with pytest.raises(ValidationError):
        PersonUpdate(name=None)
    with pytest.raises(ValidationError):
        UserUpdate(confirmed=None)


@pytest.mark.asyncio
async def test_user_repository_crud_lifecycle() -> None:
    from app.domain.users.schemas import UserCreate, UserUpdate
    from app.repositories.user_repository import UserRepository

    create_session = FakeSession()
    created = await UserRepository(create_session).create_user(
        UserCreate(email="a@example.com")
    )
    session = FakeSession(get_result=created, execute_results=[[created]])
    repository = UserRepository(session)

    assert await repository.list_users() == [created]
    assert await repository.get_user(created.user_id) is created
    assert (await repository.update_user(created.user_id, UserUpdate(confirmed=True))).confirmed
    assert await repository.delete_user(created.user_id)
    assert session.deleted == [created]


@pytest.mark.asyncio
async def test_person_repository_crud_is_scoped_to_user() -> None:
    from app.domain.users.schemas import PersonCreate, PersonUpdate
    from app.repositories.user_repository import UserRepository

    user_id = uuid4()
    create_session = FakeSession()
    created = await UserRepository(create_session).create_person(
        user_id, PersonCreate(**person_payload())
    )
    session = FakeSession(execute_results=[[created], [created], [created], [created]])
    repository = UserRepository(session)

    assert await repository.list_persons(user_id) == [created]
    assert await repository.get_person(user_id, created.person_id) is created
    updated = await repository.update_person(
        user_id, created.person_id, PersonUpdate(name="Аня")
    )
    assert updated is not None and updated.name == "Аня"
    assert await repository.delete_person(user_id, created.person_id)
    assert session.deleted == [created]


def test_users_api_crud_lifecycle(monkeypatch) -> None:
    client = users_client(monkeypatch)

    created = client.post("/api/v1/users", json={"email": "a@example.com"})
    assert created.status_code == 201
    user_id = created.json()["user_id"]
    assert client.get("/api/v1/users").json() == [created.json()]
    assert client.get(f"/api/v1/users/{user_id}").json() == created.json()
    assert client.patch(
        f"/api/v1/users/{user_id}", json={"confirmed": True}
    ).json()["confirmed"] is True
    assert client.delete(f"/api/v1/users/{user_id}").status_code == 204
    assert client.get(f"/api/v1/users/{user_id}").status_code == 404


def test_persons_api_crud_is_nested_under_owner(monkeypatch) -> None:
    client = users_client(monkeypatch)
    user_id = client.post(
        "/api/v1/users", json={"email": "a@example.com"}
    ).json()["user_id"]
    payload = {
        **person_payload(),
        "birth_date": "1990-01-02",
        "birth_time": "03:04:00",
    }

    created = client.post(f"/api/v1/users/{user_id}/persons", json=payload)
    assert created.status_code == 201
    person_id = created.json()["person_id"]
    assert client.get(f"/api/v1/users/{user_id}/persons").json() == [created.json()]
    assert client.patch(
        f"/api/v1/users/{user_id}/persons/{person_id}", json={"name": "Аня"}
    ).json()["name"] == "Аня"
    assert client.get(
        f"/api/v1/users/{uuid4()}/persons/{person_id}"
    ).status_code == 404
    assert client.delete(
        f"/api/v1/users/{user_id}/persons/{person_id}"
    ).status_code == 204


def test_application_registers_user_models_and_routes() -> None:
    import app.db.models  # noqa: F401
    from app.main import app

    assert {"users", "persons"} <= set(Base.metadata.tables)
    paths = {route.path for route in app.routes}
    assert "/api/v1/users" in paths
    assert "/api/v1/users/{user_id}/persons/{person_id}" in paths
