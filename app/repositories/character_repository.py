from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.characters.models import Character
from app.domain.characters.schemas import CharacterProfile, CharacterProfileCreate


class CharacterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _profile_data(data: CharacterProfileCreate) -> dict:
        return data.model_dump(mode="json", exclude={"name"})

    @staticmethod
    def _to_profile(row: Character) -> CharacterProfile:
        return CharacterProfile(
            character_id=row.id,
            name=row.name,
            **row.profile,
        )

    async def create(self, data: CharacterProfileCreate) -> CharacterProfile:
        row = Character(name=data.name, profile=self._profile_data(data))
        self.session.add(row)
        await self.session.flush()
        return self._to_profile(row)

    async def get_profile(self, character_id: UUID) -> CharacterProfile | None:
        row = await self.session.get(Character, character_id)
        return None if row is None else self._to_profile(row)

    async def replace_profile(
        self,
        character_id: UUID,
        data: CharacterProfileCreate,
    ) -> CharacterProfile | None:
        row = await self.session.get(Character, character_id)
        if row is None:
            return None
        row.name = data.name
        row.profile = self._profile_data(data)
        await self.session.flush()
        return self._to_profile(row)
