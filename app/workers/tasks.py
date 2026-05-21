import logging
from uuid import UUID

import anyio

from app.core.celery_app import celery_app
from app.core.config import get_settings
from app.core.database import async_session_factory
from app.repositories.generation_repository import GenerationRepository
from app.repositories.persona_repository import PersonaRepository
from app.repositories.prompt_template_repository import PromptTemplateRepository
from app.services.ai_generation_service import AIGenerationService
from app.services.natal_chart_service import NatalChartService
from app.services.openrouter_client import OpenRouterClient
from app.services.persona_context_service import PostgresPersonaContextProvider
from app.services.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


@celery_app.task(name="generate_natal_report_task")
def generate_natal_report_task(generation_id: str) -> None:
    logger.info(
        "generation task received",
        extra={"generation_id": generation_id},
    )
    anyio.run(_run_generation, generation_id)


async def _run_generation(generation_id: str) -> None:
    settings = get_settings()
    logger.info(
        "generation task started",
        extra={
            "generation_id": generation_id,
            "openrouter_model_profile": getattr(
                settings, "openrouter_model_profile", None
            ),
            "openrouter_model_report": getattr(settings, "openrouter_model_report", None),
        },
    )
    async with async_session_factory() as session:
        generation_repository = GenerationRepository(session)
        prompt_template_repository = PromptTemplateRepository(session)
        persona_repository = PersonaRepository(session)

        async with OpenRouterClient(settings=settings) as openrouter_client:
            service = AIGenerationService(
                generation_repository=generation_repository,
                prompt_template_repository=prompt_template_repository,
                natal_chart_service=NatalChartService(),
                prompt_builder=PromptBuilder(),
                persona_context_provider=PostgresPersonaContextProvider(
                    persona_repository
                ),
                openrouter_client=openrouter_client,
                settings=settings,
                commit=session.commit,
                rollback=session.rollback,
            )

            await service.generate(UUID(generation_id))
    logger.info(
        "generation task completed",
        extra={"generation_id": generation_id},
    )
