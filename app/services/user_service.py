from collections.abc import Awaitable, Callable
from uuid import UUID

from app.core.exceptions import NotFoundError
from app.domain.users.models import Person, User
from app.domain.users.schemas import PersonCreate, PersonUpdate, UserCreate, UserUpdate
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(
        self,
        repository: UserRepository,
        commit: Callable[[], Awaitable[None]],
    ) -> None:
        self.repository = repository
        self.commit = commit

    async def create_user(self, data: UserCreate) -> User:
        user = await self.repository.create_user(data)
        await self.commit()
        return user

    async def list_users(self) -> list[User]:
        return await self.repository.list_users()

    async def get_user(self, user_id: UUID) -> User:
        user = await self.repository.get_user(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    async def update_user(self, user_id: UUID, data: UserUpdate) -> User:
        user = await self.repository.update_user(user_id, data)
        if user is None:
            raise NotFoundError("User not found")
        await self.commit()
        return user

    async def delete_user(self, user_id: UUID) -> None:
        if not await self.repository.delete_user(user_id):
            raise NotFoundError("User not found")
        await self.commit()

    async def create_person(self, user_id: UUID, data: PersonCreate) -> Person:
        await self.get_user(user_id)
        person = await self.repository.create_person(user_id, data)
        await self.commit()
        return person

    async def list_persons(self, user_id: UUID) -> list[Person]:
        await self.get_user(user_id)
        return await self.repository.list_persons(user_id)

    async def get_person(self, user_id: UUID, person_id: UUID) -> Person:
        person = await self.repository.get_person(user_id, person_id)
        if person is None:
            raise NotFoundError("Person not found")
        return person

    async def update_person(
        self,
        user_id: UUID,
        person_id: UUID,
        data: PersonUpdate,
    ) -> Person:
        person = await self.repository.update_person(user_id, person_id, data)
        if person is None:
            raise NotFoundError("Person not found")
        await self.commit()
        return person

    async def delete_person(self, user_id: UUID, person_id: UUID) -> None:
        if not await self.repository.delete_person(user_id, person_id):
            raise NotFoundError("Person not found")
        await self.commit()
