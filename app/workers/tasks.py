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


@celery_app.task(name="generate_natal_report_task")
def generate_natal_report_task(generation_id: str) -> None:
    anyio.run(_run_generation, generation_id)


async def _run_generation(generation_id: str) -> None:
    settings = get_settings()
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
            )

            try:
                await service.generate(UUID(generation_id))
                await session.commit()
            except Exception:
                try:
                    await session.commit()
                except Exception:
                    await session.rollback()
                raise
