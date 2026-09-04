from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.domain.generations.astro_charts.schemas import (
    AstroChartRead,
    AstroChartUpdate,
)
from app.domain.generations.generation_neutral.schemas import (
    GenerationNeutralRead,
    GenerationNeutralUpdate,
)
from app.domain.generations.schemas import (
    GenerationCharacterReviewRead,
    GenerationCharacterReviewUpdate,
    GenerationRead,
    GenerationStylePlanRead,
    GenerationStylePlanUpdate,
    GenerationUpdate,
)
from app.repositories.character_repository import CharacterRepository
from app.repositories.generation_character_review_repository import (
    GenerationCharacterReviewRepository,
)
from app.repositories.generation_repository import GenerationRepository
from app.repositories.generation_style_plan_repository import GenerationStylePlanRepository
from app.repositories.astro_chart_repository import AstroChartRepository
from app.repositories.generation_neutral_repository import (
    GenerationNeutralRepository,
)
from app.repositories.user_repository import UserRepository
from app.services.astro_chart_service import AstroChartService
from app.services.chart_image_storage import ChartImageStorage
from app.services.generation_neutral_service import GenerationNeutralService
from app.services.generation_character_review_service import GenerationCharacterReviewService
from app.services.generation_service import GenerationService
from app.services.generation_style_plan_service import GenerationStylePlanService

router = APIRouter(prefix="/generations", tags=["generations"])


def get_astro_chart_service(
    session: AsyncSession = Depends(get_session),
) -> AstroChartService:
    return AstroChartService(
        AstroChartRepository(session),
        UserRepository(session),
        ChartImageStorage(get_settings()),
        session.commit,
    )


def get_generation_neutral_service(
    session: AsyncSession = Depends(get_session),
) -> GenerationNeutralService:
    return GenerationNeutralService(
        GenerationNeutralRepository(session),
        UserRepository(session),
        session.commit,
    )


def get_generation_service(
    session: AsyncSession = Depends(get_session),
) -> GenerationService:
    return GenerationService(
        GenerationRepository(session),
        UserRepository(session),
        CharacterRepository(session),
        session.commit,
    )


def get_generation_style_plan_service(
    session: AsyncSession = Depends(get_session),
) -> GenerationStylePlanService:
    return GenerationStylePlanService(
        GenerationStylePlanRepository(session),
        GenerationRepository(session),
        session.commit,
    )


def get_generation_character_review_service(
    session: AsyncSession = Depends(get_session),
) -> GenerationCharacterReviewService:
    return GenerationCharacterReviewService(
        GenerationCharacterReviewRepository(session),
        GenerationRepository(session),
        session.commit,
    )


@router.get("/astro-charts", response_model=list[AstroChartRead])
async def list_astro_charts(
    person_id: UUID,
    service: AstroChartService = Depends(get_astro_chart_service),
) -> list[AstroChartRead]:
    return await service.list(person_id)


@router.get("/astro-charts/{chart_id}", response_model=AstroChartRead)
async def get_astro_chart(
    chart_id: UUID,
    service: AstroChartService = Depends(get_astro_chart_service),
) -> AstroChartRead:
    return await service.get(chart_id)


@router.patch("/astro-charts/{chart_id}", response_model=AstroChartRead)
async def update_astro_chart(
    chart_id: UUID,
    payload: AstroChartUpdate,
    service: AstroChartService = Depends(get_astro_chart_service),
) -> AstroChartRead:
    return await service.update(chart_id, payload)


@router.delete(
    "/astro-charts/{chart_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_astro_chart(
    chart_id: UUID,
    service: AstroChartService = Depends(get_astro_chart_service),
) -> Response:
    await service.delete(chart_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/neutral", response_model=list[GenerationNeutralRead])
async def list_generation_neutral(
    person_id: UUID,
    service: GenerationNeutralService = Depends(get_generation_neutral_service),
) -> list[GenerationNeutralRead]:
    return await service.list(person_id)


@router.get("/neutral/{generation_id}", response_model=GenerationNeutralRead)
async def get_generation_neutral(
    generation_id: UUID,
    service: GenerationNeutralService = Depends(get_generation_neutral_service),
) -> GenerationNeutralRead:
    return await service.get(generation_id)


@router.patch("/neutral/{generation_id}", response_model=GenerationNeutralRead)
async def update_generation_neutral(
    generation_id: UUID,
    payload: GenerationNeutralUpdate,
    service: GenerationNeutralService = Depends(get_generation_neutral_service),
) -> GenerationNeutralRead:
    return await service.update(generation_id, payload)


@router.delete(
    "/neutral/{generation_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_generation_neutral(
    generation_id: UUID,
    service: GenerationNeutralService = Depends(get_generation_neutral_service),
) -> Response:
    await service.delete(generation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/style-plans", response_model=list[GenerationStylePlanRead])
async def list_generation_style_plans(
    generation_id: UUID,
    service: GenerationStylePlanService = Depends(get_generation_style_plan_service),
) -> list[GenerationStylePlanRead]:
    return await service.list(generation_id)


@router.get("/style-plans/{plan_id}", response_model=GenerationStylePlanRead)
async def get_generation_style_plan(
    plan_id: UUID,
    service: GenerationStylePlanService = Depends(get_generation_style_plan_service),
) -> GenerationStylePlanRead:
    return await service.get(plan_id)


@router.patch("/style-plans/{plan_id}", response_model=GenerationStylePlanRead)
async def update_generation_style_plan(
    plan_id: UUID,
    payload: GenerationStylePlanUpdate,
    service: GenerationStylePlanService = Depends(get_generation_style_plan_service),
) -> GenerationStylePlanRead:
    return await service.update(plan_id, payload)


@router.delete("/style-plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generation_style_plan(
    plan_id: UUID,
    service: GenerationStylePlanService = Depends(get_generation_style_plan_service),
) -> Response:
    await service.delete(plan_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/character-reviews", response_model=list[GenerationCharacterReviewRead]
)
async def list_generation_character_reviews(
    generation_id: UUID,
    service: GenerationCharacterReviewService = Depends(
        get_generation_character_review_service
    ),
) -> list[GenerationCharacterReviewRead]:
    return await service.list(generation_id)


@router.get(
    "/character-reviews/{review_id}", response_model=GenerationCharacterReviewRead
)
async def get_generation_character_review(
    review_id: UUID,
    service: GenerationCharacterReviewService = Depends(
        get_generation_character_review_service
    ),
) -> GenerationCharacterReviewRead:
    return await service.get(review_id)


@router.patch(
    "/character-reviews/{review_id}", response_model=GenerationCharacterReviewRead
)
async def update_generation_character_review(
    review_id: UUID,
    payload: GenerationCharacterReviewUpdate,
    service: GenerationCharacterReviewService = Depends(
        get_generation_character_review_service
    ),
) -> GenerationCharacterReviewRead:
    return await service.update(review_id, payload)


@router.delete(
    "/character-reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_generation_character_review(
    review_id: UUID,
    service: GenerationCharacterReviewService = Depends(
        get_generation_character_review_service
    ),
) -> Response:
    await service.delete(review_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=list[GenerationRead])
async def list_generations(
    person_id: UUID,
    service: GenerationService = Depends(get_generation_service),
) -> list[GenerationRead]:
    return await service.list(person_id)


@router.get("/{generation_id}", response_model=GenerationRead)
async def get_generation(
    generation_id: UUID,
    service: GenerationService = Depends(get_generation_service),
) -> GenerationRead:
    return await service.get(generation_id)


@router.patch("/{generation_id}", response_model=GenerationRead)
async def update_generation(
    generation_id: UUID,
    payload: GenerationUpdate,
    service: GenerationService = Depends(get_generation_service),
) -> GenerationRead:
    return await service.update(generation_id, payload)


@router.delete("/{generation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_generation(
    generation_id: UUID,
    service: GenerationService = Depends(get_generation_service),
) -> Response:
    await service.delete(generation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
