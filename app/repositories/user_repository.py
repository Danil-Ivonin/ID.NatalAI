from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.users.models import Person, User
from app.domain.users.schemas import PersonCreate, PersonUpdate, UserCreate, UserUpdate


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_user(self, data: UserCreate) -> User:
        user = User(**data.model_dump())
        self.session.add(user)
        await self.session.flush()
        return user

    async def list_users(self) -> list[User]:
        result = await self.session.execute(select(User).order_by(User.user_id))
        return list(result.scalars().all())

    async def get_user(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_person_by_id(self, person_id: UUID) -> Person | None:
        return await self.session.get(Person, person_id)

    async def update_user(self, user_id: UUID, data: UserUpdate) -> User | None:
        user = await self.get_user(user_id)
        if user is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(user, field, value)
        await self.session.flush()
        return user

    async def delete_user(self, user_id: UUID) -> bool:
        user = await self.get_user(user_id)
        if user is None:
            return False
        await self.session.delete(user)
        return True

    async def create_person(self, user_id: UUID, data: PersonCreate) -> Person:
        person = Person(user_id=user_id, **data.model_dump())
        self.session.add(person)
        await self.session.flush()
        return person

    async def list_persons(self, user_id: UUID) -> list[Person]:
        result = await self.session.execute(
            select(Person).where(Person.user_id == user_id).order_by(Person.person_id)
        )
        return list(result.scalars().all())

    async def get_person(self, user_id: UUID, person_id: UUID) -> Person | None:
        result = await self.session.execute(
            select(Person).where(
                Person.user_id == user_id,
                Person.person_id == person_id,
            )
        )
        return result.scalar_one_or_none()

    async def update_person(
        self,
        user_id: UUID,
        person_id: UUID,
        data: PersonUpdate,
    ) -> Person | None:
        person = await self.get_person(user_id, person_id)
        if person is None:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(person, field, value)
        await self.session.flush()
        return person

    async def delete_person(self, user_id: UUID, person_id: UUID) -> bool:
        person = await self.get_person(user_id, person_id)
        if person is None:
            return False
        await self.session.delete(person)
        return True
