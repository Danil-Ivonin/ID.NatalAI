from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401
from app.domain.prompts.enums import PromptTemplateType
from app.domain.prompts.models import PromptTemplate
from app.domain.prompts.schemas import PromptTemplateCreate


class PromptTemplateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: PromptTemplateCreate) -> PromptTemplate:
        template = PromptTemplate(**data.model_dump())
        self.session.add(template)
        await self.session.flush()
        await self.session.refresh(template)
        return template

    async def list(
        self, template_type: PromptTemplateType | None = None
    ) -> list[PromptTemplate]:
        statement = select(PromptTemplate).order_by(
            PromptTemplate.type, PromptTemplate.version
        )
        if template_type is not None:
            statement = statement.where(PromptTemplate.type == template_type)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def get(self, template_id: UUID) -> PromptTemplate | None:
        return await self.session.get(PromptTemplate, template_id)

    async def get_active(
        self, template_type: PromptTemplateType
    ) -> PromptTemplate | None:
        statement = select(PromptTemplate).where(
            PromptTemplate.type == template_type,
            PromptTemplate.is_active.is_(True),
        )
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def activate(self, template_id: UUID) -> PromptTemplate | None:
        target = await self.get(template_id)
        if target is None:
            return None

        templates = await self.list(target.type)
        for template in templates:
            template.is_active = template.id == target.id

        await self.session.flush()
        await self.session.refresh(target)
        return target
