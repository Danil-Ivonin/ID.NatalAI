import datetime
import logging
import uuid
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.domain.generation.ai_schemas import StyledNatalReport, ReportSection
from app.domain.generation.enums import GenerationStatus
from app.domain.generation.schemas import (
    ChartImageResponse,
    GenerationCreate,
    GenerationCreateResponse,
    GenerationDetailResponse,
)
from app.repositories.generation_repository import GenerationRepository
from app.repositories.persona_repository import PersonaRepository
from app.services.chart_image_storage import ChartImageStorage

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
            "birth_timezone": payload.birth_place.timezone,
        },
    )
    persona_repository = PersonaRepository(session)
    persona = await persona_repository.get(payload.persona_id)
    if persona is None:
        logger.warning(
            "generation create rejected: persona not found",
            extra={"persona_id": str(payload.persona_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found",
        )

    generation_repository = GenerationRepository(session)
    generation = await generation_repository.create(payload)
    await session.commit()
    logger.info(
        "generation record created",
        extra={
            "generation_id": str(generation.id),
            "persona_id": str(payload.persona_id),
            "status": str(generation.status),
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
    # return GenerationDetailResponse(generation_id=str(generation_id), status=GenerationStatus.COMPLETED, result_text=StyledNatalReport(
    #     title="Тест разбор",
    #     intro=ReportSection(title="Интро", text="текст интро"),
    #     general=ReportSection(title="Общая информация", text="текст общей информации"),
    # love_and_sex=ReportSection(title="Любовь и секс", text="текст любовь и секс"),
    # career_and_money=ReportSection(title="Карьера и деньги", text="текст карьера и деньги"),
    # demons=ReportSection(title="Демоны", text="текст демоны"),
    # final_summary=ReportSection(title="Итоги", text="Итоги текст"),
    # ), created_at=datetime.now())
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
            "status": str(generation.status),
            "has_result": generation.result_json is not None,
            "has_error": generation.error_message is not None,
        },
    )
    response = GenerationDetailResponse.model_validate(generation)
    object_key = getattr(generation, "chart_image_object_key", None)
    mime_type = getattr(generation, "chart_image_mime_type", None)
    if object_key is not None and mime_type is not None:
        storage = ChartImageStorage(get_settings())
        response.chart_image = ChartImageResponse(
            url=storage.presigned_url(object_key),
            mime_type=mime_type,
        )
    return response
