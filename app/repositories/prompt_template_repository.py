from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

import app.db.models  # noqa: F401
from app.domain.prompts.enums import PromptTemplateType
from app.domain.prompts.models import PromptTemplate
from app.domain.prompts.schemas import PromptTemplateCreate


class PromptTemplateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, data: PromptTemplateCreate) -> PromptTemplate:
        if data.is_active:
            await self._deactivate_active_templates(data.type)
            await self.session.flush()

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

        await self._deactivate_active_templates(target.type, exclude_id=target.id)
        await self.session.flush()
        target.is_active = True
        await self.session.flush()
        await self.session.refresh(target)
        return target

    async def _deactivate_active_templates(
        self,
        template_type: PromptTemplateType,
        exclude_id: UUID | None = None,
    ) -> None:
        statement = (
            update(PromptTemplate)
            .where(
                PromptTemplate.type == template_type,
                PromptTemplate.is_active.is_(True),
            )
            .values(is_active=False)
        )
        if exclude_id is not None:
            statement = statement.where(PromptTemplate.id != exclude_id)
        await self.session.execute(statement)
