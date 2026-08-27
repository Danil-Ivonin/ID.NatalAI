from sqlalchemy import case, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.characters.models import CharacterExample as CharacterExampleRow
from app.domain.characters.schemas import (
    CharacterExample,
    CharacterExampleCreate,
    CharacterExampleEmbedding,
    CharacterExampleSearch,
)


class CharacterExampleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _to_example(row: CharacterExampleRow) -> CharacterExample:
        return CharacterExample(
            id=row.id,
            character_id=row.character_id,
            raw_text=row.raw_text,
            clean_text=row.clean_text,
            context=row.context,
            emotion=row.emotion,
            rhetorical_function=row.rhetorical_function,
            humor_types=row.humor_types,
            speech_patterns=row.speech_patterns,
            embedding=None if row.embedding is None else list(row.embedding),
            active=row.active,
        )

    async def create(self, data: CharacterExampleCreate) -> CharacterExample:
        row = CharacterExampleRow(**data.model_dump())
        self.session.add(row)
        await self.session.flush()
        return self._to_example(row)

    async def set_embedding(
        self,
        example_id: int,
        data: CharacterExampleEmbedding,
    ) -> CharacterExample | None:
        row = await self.session.get(CharacterExampleRow, example_id)
        if row is None:
            return None
        row.embedding = data.embedding
        await self.session.flush()
        return self._to_example(row)

    async def set_active(
        self,
        example_id: int,
        active: bool,
    ) -> CharacterExample | None:
        row = await self.session.get(CharacterExampleRow, example_id)
        if row is None:
            return None
        row.active = active
        await self.session.flush()
        return self._to_example(row)

    async def search(
        self,
        data: CharacterExampleSearch,
    ) -> list[CharacterExample]:
        distance = CharacterExampleRow.embedding.cosine_distance(data.embedding)
        bonus = case(
            (CharacterExampleRow.emotion == data.emotion, 0.05),
            else_=0.0,
        )
        if data.humor_types:
            bonus += case(
                (CharacterExampleRow.humor_types.overlap(data.humor_types), 0.025),
                else_=0.0,
            )
        if data.speech_patterns:
            bonus += case(
                (
                    CharacterExampleRow.speech_patterns.overlap(data.speech_patterns),
                    0.025,
                ),
                else_=0.0,
            )

        statement = select(CharacterExampleRow).where(
            CharacterExampleRow.character_id == data.character_id,
            CharacterExampleRow.active.is_(True),
            CharacterExampleRow.embedding.is_not(None),
        )
        if data.exclude_ids:
            statement = statement.where(
                CharacterExampleRow.id.not_in(data.exclude_ids)
            )
        statement = statement.order_by(distance - bonus, CharacterExampleRow.id).limit(
            data.limit
        )
        result = await self.session.execute(statement)
        return [self._to_example(row) for row in result.scalars().all()]
