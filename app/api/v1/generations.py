import logging
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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/generations", tags=["generations"])


def dispatch_generation_job(generation_id: UUID) -> None:
    """Dispatch background generation while keeping tests monkeypatchable."""
    from app.workers.tasks import generate_natal_report_task

    logger.info(
        "dispatching generation job",
        extra={"generation_id": str(generation_id)},
    )
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
    logger.info(
        "generation create request received",
        extra={
            "persona_id": str(payload.persona_id),
            "has_person_name": payload.person_name is not None,
            "birth_city": payload.birth_place.city,
            "birth_country": payload.birth_place.country,
            "birth_timezone": payload.birth_place.timezone,
        },
    )
    persona_repository = PersonaRepository(session)
    persona = await persona_repository.get_active(payload.persona_id)
    if persona is None:
        logger.warning(
            "generation create rejected: active persona not found",
            extra={"persona_id": str(payload.persona_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active persona not found",
        )

    generation_repository = GenerationRepository(session)
    generation = await generation_repository.create(payload)
    await session.commit()
    logger.info(
        "generation record created",
        extra={
            "generation_id": str(generation.id),
            "persona_id": str(payload.persona_id),
            "status": generation.status.value,
        },
    )
    dispatch_generation_job(generation.id)
    return GenerationCreateResponse.model_validate(generation)


@router.get("/{generation_id}", response_model=GenerationDetailResponse)
async def get_generation(
    generation_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> GenerationDetailResponse:
    logger.info(
        "generation detail requested",
        extra={"generation_id": str(generation_id)},
    )
    repository = GenerationRepository(session)
    generation = await repository.get(generation_id)
    if generation is None:
        logger.warning(
            "generation detail not found",
            extra={"generation_id": str(generation_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Generation not found",
        )
    logger.info(
        "generation detail loaded",
        extra={
            "generation_id": str(generation_id),
            "status": generation.status.value,
            "has_result": generation.result_text is not None,
            "has_error": generation.error_message is not None,
        },
    )
    return GenerationDetailResponse.model_validate(generation)
