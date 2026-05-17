from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domain.prompts.enums import PromptTemplateType
from app.domain.prompts.schemas import (
    PromptTemplateActivateResponse,
    PromptTemplateCreate,
    PromptTemplateRead,
)
from app.repositories.prompt_template_repository import PromptTemplateRepository

router = APIRouter(prefix="/prompt-templates", tags=["prompt-templates"])


@router.post("", response_model=PromptTemplateRead, status_code=status.HTTP_201_CREATED)
async def create_prompt_template(
    payload: PromptTemplateCreate,
    session: AsyncSession = Depends(get_session),
) -> PromptTemplateRead:
    repository = PromptTemplateRepository(session)
    template = await repository.create(payload)
    await session.commit()
    return PromptTemplateRead.model_validate(template)


@router.get("", response_model=list[PromptTemplateRead])
async def list_prompt_templates(
    type: PromptTemplateType | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> list[PromptTemplateRead]:
    repository = PromptTemplateRepository(session)
    templates = await repository.list(type)
    return [PromptTemplateRead.model_validate(template) for template in templates]


@router.get("/active", response_model=PromptTemplateRead)
async def get_active_prompt_template(
    type: PromptTemplateType,
    session: AsyncSession = Depends(get_session),
) -> PromptTemplateRead:
    repository = PromptTemplateRepository(session)
    template = await repository.get_active(type)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active prompt template not found",
        )
    return PromptTemplateRead.model_validate(template)


@router.post(
    "/{template_id}/activate",
    response_model=PromptTemplateActivateResponse,
)
async def activate_prompt_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> PromptTemplateActivateResponse:
    repository = PromptTemplateRepository(session)
    template = await repository.activate(template_id)
    if template is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt template not found",
        )
    await session.commit()
    return PromptTemplateActivateResponse.model_validate(template)
