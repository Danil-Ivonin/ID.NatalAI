from uuid import UUID

import anyio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.repositories.astro_chart_repository import AstroChartRepository
from app.repositories.character_repository import CharacterRepository
from app.repositories.generation_character_block_repository import (
    GenerationCharacterBlockRepository,
)
from app.repositories.generation_neutral_repository import GenerationNeutralRepository
from app.repositories.generation_repository import GenerationRepository
from app.repositories.generation_style_plan_repository import GenerationStylePlanRepository
from app.repositories.user_repository import UserRepository
from app.services.chart_image_storage import ChartImageStorage
from app.services.free_generation_service import FreeGenerationService
from app.services.natal_chart_service import NatalChartService
from app.services.openrouter_client import OpenRouterClient


@celery_app.task(bind=True, name="generate_free")
def generate_free(task, person_id: str, character_id: str) -> dict:
    return anyio.run(
        _run_free_generation, task, UUID(person_id), UUID(character_id)
    )


async def _run_free_generation(task, person_id: UUID, character_id: UUID) -> dict:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    completed_stages = []

    def progress(event: dict[str, str]) -> None:
        completed_stages.append(event)
        task.update_state(
            state="PROGRESS",
            meta={"completed_stages": completed_stages.copy()},
        )

    try:
        async with session_factory() as session:
            async with OpenRouterClient(settings=settings) as openrouter:
                service = FreeGenerationService(
                    generation_repository=GenerationRepository(session),
                    astro_chart_repository=AstroChartRepository(session),
                    neutral_repository=GenerationNeutralRepository(session),
                    style_plan_repository=GenerationStylePlanRepository(session),
                    character_block_repository=GenerationCharacterBlockRepository(
                        session
                    ),
                    user_repository=UserRepository(session),
                    character_repository=CharacterRepository(session),
                    natal_chart_service=NatalChartService(),
                    storage=ChartImageStorage(settings),
                    openrouter=openrouter,
                    settings=settings,
                    commit=session.commit,
                    rollback=session.rollback,
                )
                result = await service.generate(person_id, character_id, progress)
                return {**result, "completed_stages": completed_stages}
    finally:
        await engine.dispose()
