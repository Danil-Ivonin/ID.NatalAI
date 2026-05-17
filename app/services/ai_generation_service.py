from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

import orjson
from pydantic import BaseModel

from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.domain.generation.ai_schemas import AstrologyProfile, StyledNatalReport
from app.domain.generation.enums import GenerationStage, GenerationStatus
from app.domain.persona.context import PersonaContextProvider
from app.domain.prompts.enums import PromptTemplateType
from app.repositories.generation_repository import GenerationRepository
from app.repositories.prompt_template_repository import PromptTemplateRepository
from app.services.natal_chart_service import NatalChartService
from app.services.openrouter_client import OpenRouterClient, OpenRouterChatResult
from app.services.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class AIGenerationService:
    provider = "openrouter"

    def __init__(
        self,
        generation_repository: GenerationRepository,
        prompt_template_repository: PromptTemplateRepository,
        natal_chart_service: NatalChartService,
        prompt_builder: PromptBuilder,
        persona_context_provider: PersonaContextProvider,
        openrouter_client: OpenRouterClient,
        settings: Settings | None = None,
    ) -> None:
        self.generation_repository = generation_repository
        self.prompt_template_repository = prompt_template_repository
        self.natal_chart_service = natal_chart_service
        self.prompt_builder = prompt_builder
        self.persona_context_provider = persona_context_provider
        self.openrouter_client = openrouter_client
        self.settings = settings or get_settings()

    async def generate(self, generation_id: UUID) -> None:
        generation = await self.generation_repository.get(generation_id)
        if generation is None:
            raise NotFoundError(f"Generation not found: {generation_id}")

        stage: GenerationStage | None = None
        model: str | None = None
        template = None
        messages: list[dict[str, Any]] | None = None
        response_format: dict[str, Any] | None = None

        try:
            await self.generation_repository.set_status(
                generation_id, GenerationStatus.PROCESSING
            )

            stage = GenerationStage.NATAL_CHART_BUILD
            chart = self.natal_chart_service.build_natal_chart(
                person_name=generation.person_name,
                gender=generation.gender,
                birth_date=generation.birth_date,
                birth_time=generation.birth_time,
                lat=generation.birth_lat,
                lng=generation.birth_lng,
                timezone=generation.birth_timezone,
            )
            await self.generation_repository.save_natal_xml(
                generation_id, chart.natal_xml
            )
            await self._create_success_run(
                generation_id=generation_id,
                stage=stage,
                provider="kerykeion",
                model="local",
                template=None,
                raw_request={"birth_data": "[redacted]"},
                raw_response={"natal_xml_saved": True},
                result=None,
            )

            stage = GenerationStage.ASTROLOGY_PROFILE_EXTRACTION
            model = self.settings.openrouter_model_profile
            template = await self._active_template(
                PromptTemplateType.ASTROLOGY_PROFILE_EXTRACTION
            )
            messages = self.prompt_builder.build_astrology_profile_prompt(
                natal_xml=chart.natal_xml,
                person_name=generation.person_name,
                gender=generation.gender,
                template_content=template.content,
            )
            response_format = self._json_schema_response_format(AstrologyProfile)
            profile_result = await self.openrouter_client.chat_completion(
                model=model,
                messages=messages,
                response_format=response_format,
            )
            profile = AstrologyProfile.model_validate(
                self._parse_json_content(profile_result.content)
            )
            profile_json = profile.model_dump(mode="json")
            await self.generation_repository.save_profile(generation_id, profile_json)
            await self._create_success_run(
                generation_id=generation_id,
                stage=stage,
                provider=self.provider,
                model=model,
                template=template,
                raw_request=self._raw_request(model, response_format),
                raw_response=profile_result.raw_response,
                result=profile_result,
            )

            stage = GenerationStage.STYLED_REPORT_GENERATION
            model = self.settings.openrouter_model_report
            persona_context = await self.persona_context_provider.get_context(
                generation.persona_id
            )
            template = await self._active_template(
                PromptTemplateType.STYLED_REPORT_GENERATION
            )
            messages = self.prompt_builder.build_styled_report_prompt(
                astrology_profile_json=profile_json,
                persona_context=persona_context,
                person_name=generation.person_name,
                gender=generation.gender,
                template_content=template.content,
            )
            response_format = self._json_schema_response_format(StyledNatalReport)
            report_result = await self.openrouter_client.chat_completion(
                model=model,
                messages=messages,
                response_format=response_format,
            )
            report = StyledNatalReport.model_validate(
                self._parse_json_content(report_result.content)
            )
            report_json = report.model_dump(mode="json")
            await self.generation_repository.save_result(
                generation_id,
                report_json,
                self._report_text(report),
            )
            await self._create_success_run(
                generation_id=generation_id,
                stage=stage,
                provider=self.provider,
                model=model,
                template=template,
                raw_request=self._raw_request(model, response_format),
                raw_response=report_result.raw_response,
                result=report_result,
            )
        except Exception as exc:
            error_message = str(exc)
            await self.generation_repository.fail(generation_id, error_message)
            if stage is not None:
                await self._create_error_run(
                    generation_id=generation_id,
                    stage=stage,
                    provider=self.provider if stage != GenerationStage.NATAL_CHART_BUILD else "kerykeion",
                    model=model or "local",
                    template=template,
                    raw_request=self._raw_request(model, response_format)
                    if messages is not None
                    else None,
                    error_message=error_message,
                )
            logger.exception(
                "generation failed",
                extra={
                    "generation_id": str(generation_id),
                    "stage": stage.value if stage is not None else None,
                    "provider": self.provider,
                    "model": model,
                },
            )
            raise

    async def _active_template(self, template_type: PromptTemplateType):
        template = await self.prompt_template_repository.get_active(template_type)
        if template is None:
            raise NotFoundError(f"Active prompt template not found: {template_type}")
        return template

    async def _create_success_run(
        self,
        generation_id: UUID,
        stage: GenerationStage,
        provider: str,
        model: str,
        template: Any,
        raw_request: dict[str, Any] | None,
        raw_response: dict[str, Any] | None,
        result: OpenRouterChatResult | None,
    ) -> None:
        await self.generation_repository.create_run(
            {
                "generation_id": generation_id,
                "stage": stage,
                "provider": provider,
                "model": model,
                "prompt_template_id": getattr(template, "id", None),
                "prompt_template_version": getattr(template, "version", None),
                "input_tokens": None if result is None else result.input_tokens,
                "output_tokens": None if result is None else result.output_tokens,
                "raw_request": raw_request,
                "raw_response": raw_response,
                "error_message": None,
                "latency_ms": None if result is None else result.latency_ms,
            }
        )

    async def _create_error_run(
        self,
        generation_id: UUID,
        stage: GenerationStage,
        provider: str,
        model: str,
        template: Any,
        raw_request: dict[str, Any] | None,
        error_message: str,
    ) -> None:
        await self.generation_repository.create_run(
            {
                "generation_id": generation_id,
                "stage": stage,
                "provider": provider,
                "model": model,
                "prompt_template_id": getattr(template, "id", None),
                "prompt_template_version": getattr(template, "version", None),
                "input_tokens": None,
                "output_tokens": None,
                "raw_request": raw_request,
                "raw_response": None,
                "error_message": error_message,
                "latency_ms": None,
            }
        )

    @staticmethod
    def _parse_json_content(content: str) -> Any:
        return orjson.loads(content)

    @staticmethod
    def _json_schema_response_format(model: type[BaseModel]) -> dict[str, Any]:
        return {
            "type": "json_schema",
            "json_schema": {
                "name": model.__name__,
                "strict": True,
                "schema": model.model_json_schema(),
            },
        }

    @staticmethod
    def _raw_request(
        model: str | None,
        response_format: dict[str, Any] | None,
    ) -> dict[str, Any]:
        return {
            "model": model,
            "messages": "[redacted]",
            "response_format": response_format,
        }

    @staticmethod
    def _report_text(report: StyledNatalReport) -> str:
        parts = [report.title]
        for section in [
            report.intro,
            report.general,
            report.love_and_sex,
            report.career_and_money,
            report.demons,
            report.final_summary,
        ]:
            parts.append(f"{section.title}\n{section.text}")
        return "\n\n".join(parts)
