from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domain.generation.schemas import (
    GenerationCreate,
    GenerationCreateResponse,
    GenerationDetailResponse,
)
from app.repositories.generation_repository import GenerationRepository
from app.repositories.persona_repository import PersonaRepository

router = APIRouter(prefix="/generations", tags=["generations"])


def dispatch_generation_job(generation_id: UUID) -> None:
    """Dispatch background generation while keeping tests monkeypatchable."""
    try:
        from app.workers.tasks import generate_natal_report_task
    except ModuleNotFoundError:
        return

    generate_natal_report_task.delay(str(generation_id))


@router.post(
    "",
    response_model=GenerationCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_generation(
    payload: GenerationCreate,
    session: AsyncSession = Depends(get_session),
) -> GenerationCreateResponse:
    persona_repository = PersonaRepository(session)
    persona = await persona_repository.get_active(payload.persona_id)
    if persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active persona not found",
        )

    generation_repository = GenerationRepository(session)
    generation = await generation_repository.create(payload)
    await session.commit()
    dispatch_generation_job(generation.id)
    return GenerationCreateResponse.model_validate(generation)


@router.get("/{generation_id}", response_model=GenerationDetailResponse)
async def get_generation(
    generation_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> GenerationDetailResponse:
    repository = GenerationRepository(session)
    generation = await repository.get(generation_id)
    if generation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found",
        )
    return GenerationDetailResponse.model_validate(generation)
