from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.domain.generations.astro_charts.schemas import (
    AstroChartCreate,
    AstroChartRead,
    AstroChartUpdate,
)
from app.domain.generations.generation_neutral.schemas import (
    GenerationNeutralCreate,
    GenerationNeutralRead,
    GenerationNeutralUpdate,
)
from app.repositories.astro_chart_repository import AstroChartRepository
from app.repositories.generation_neutral_repository import (
    GenerationNeutralRepository,
)
from app.repositories.user_repository import UserRepository
from app.services.astro_chart_service import AstroChartService
from app.services.chart_image_storage import ChartImageStorage
from app.services.generation_neutral_service import GenerationNeutralService

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


@router.post(
    "/astro-charts",
    response_model=AstroChartRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_astro_chart(
    payload: AstroChartCreate,
    service: AstroChartService = Depends(get_astro_chart_service),
) -> AstroChartRead:
    return await service.create(payload)


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


@router.post(
    "/neutral",
    response_model=GenerationNeutralRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_generation_neutral(
    payload: GenerationNeutralCreate,
    service: GenerationNeutralService = Depends(get_generation_neutral_service),
) -> GenerationNeutralRead:
    return await service.create(payload)


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
