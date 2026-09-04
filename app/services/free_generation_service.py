from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

import orjson
from pydantic import BaseModel

from app.core.config import Settings
from app.core.exceptions import NotFoundError
from app.domain.generations.astro_charts.schemas import AstroChartCreate
from app.domain.generations.generation_neutral.schemas import GenerationNeutralCreate, GenerationNeutralResult
from app.domain.generations.schemas import (
    BlockStylePlan,
    CharacterBlockResult,
    GenerationBlock,
    GenerationCharacterBlockCreate,
    GenerationCreate,
    GenerationProcessStatus,
    GenerationStatus,
    GenerationStylePlanCreate,
    GenerationUpdate,
)
from app.repositories.astro_chart_repository import AstroChartRepository
from app.repositories.character_repository import CharacterRepository
from app.repositories.generation_character_block_repository import GenerationCharacterBlockRepository
from app.repositories.generation_neutral_repository import GenerationNeutralRepository
from app.repositories.generation_repository import GenerationRepository
from app.repositories.generation_style_plan_repository import GenerationStylePlanRepository
from app.repositories.user_repository import UserRepository
from app.services.chart_image_storage import ChartImageStorage
from app.services.natal_chart_service import NatalChartService
from app.services.openrouter_client import OpenRouterChatResult, OpenRouterClient
from app.services.prompt_builder import PromptBuilder

Progress = Callable[[dict[str, str]], None]


class FreeGenerationService:
    def __init__(
        self,
        generation_repository: GenerationRepository,
        astro_chart_repository: AstroChartRepository,
        neutral_repository: GenerationNeutralRepository,
        style_plan_repository: GenerationStylePlanRepository,
        character_block_repository: GenerationCharacterBlockRepository,
        user_repository: UserRepository,
        character_repository: CharacterRepository,
        natal_chart_service: NatalChartService,
        storage: ChartImageStorage,
        openrouter: OpenRouterClient,
        settings: Settings,
        commit: Callable[[], Awaitable[None]],
        rollback: Callable[[], Awaitable[None]],
    ) -> None:
        self.generations = generation_repository
        self.charts = astro_chart_repository
        self.neutrals = neutral_repository
        self.plans = style_plan_repository
        self.blocks = character_block_repository
        self.users = user_repository
        self.characters = character_repository
        self.natal_chart = natal_chart_service
        self.storage = storage
        self.openrouter = openrouter
        self.settings = settings
        self.commit = commit
        self.rollback = rollback
        self.prompt_builder = PromptBuilder()

    async def generate(
        self, person_id: UUID, character_id: UUID, progress: Progress
    ) -> dict[str, Any]:
        person = await self.users.get_person_by_id(person_id)
        if person is None:
            raise NotFoundError("Person not found")
        character = await self.characters.get_profile(character_id)
        if character is None:
            raise NotFoundError("Character not found")

        generation_id: UUID | None = None
        try:
            generation = await self.generations.create(
                GenerationCreate(
                    person_id=person_id,
                    character_id=character_id,
                    status=GenerationProcessStatus.PROCESSING,
                )
            )
            generation_id = generation.generation_id
            await self.commit()
            self._progress(progress, "generation_created", generation_id)

            chart = self.natal_chart.build_natal_chart(
                person_name=person.name,
                gender=getattr(person.sex, "value", person.sex),
                birth_date=person.birth_date,
                birth_time=person.birth_time,
                lat=person.birth_lat,
                lng=person.birth_lng,
                timezone=person.birth_timezone,
                city=person.birth_city,
                nation=person.birth_nation,
            )
            chart_key = f"generations/{generation_id}/natal-chart.svg"
            await self.storage.upload(
                chart_key, chart.chart_svg.encode(), "image/svg+xml"
            )
            await self.charts.create(
                AstroChartCreate(
                    person_id=person_id,
                    generation_id=generation_id,
                    natal_xml=chart.natal_xml,
                    chart_svg=chart.chart_svg,
                )
            )
            await self.commit()
            self._progress(progress, "astro_chart_created", generation_id)

            character_json = character.model_dump(mode="json")
            subject = {
                "display_name": person.name,
                "sex": getattr(person.sex, "value", person.sex),
            }
            neutral_messages = self.prompt_builder.build_neutral(subject, chart.natal_xml)
            neutral_call = await self._chat(
                self.settings.openrouter_model_profile,
                neutral_messages,
                GenerationNeutralResult,
            )
            neutral = GenerationNeutralResult.model_validate(
                orjson.loads(neutral_call.content)
            )
            await self.neutrals.create(
                GenerationNeutralCreate(
                    person_id=person_id,
                    generation_id=generation_id,
                    used_model=self.settings.openrouter_model_profile,
                    prompt=self._dump(neutral_messages),
                    token_usage=self._usage(neutral_call),
                    result=neutral,
                )
            )
            await self.commit()
            self._progress(progress, "neutral_generated", generation_id)

            general_block = neutral.blocks[0]
            intro_messages = self.prompt_builder.build_intro(
                character_json, subject, general_block
            )
            intro_call = await self._chat(
                self.settings.openrouter_model_report,
                intro_messages,
                CharacterBlockResult,
            )
            intro = CharacterBlockResult.model_validate(orjson.loads(intro_call.content))
            await self.blocks.create(
                GenerationCharacterBlockCreate(
                    generation_id=generation_id,
                    block=GenerationBlock.INTRO,
                    status=GenerationStatus.COMPLETED,
                    used_model=self.settings.openrouter_model_report,
                    prompt=self._dump(intro_messages),
                    token_usage=self._usage(intro_call),
                    result=intro.model_dump(mode="json"),
                )
            )
            await self.commit()
            self._progress(progress, "intro_generated", generation_id)

            await self.generations.update(
                generation_id,
                GenerationUpdate(
                    current_block=GenerationBlock.GENERAL,
                    status=GenerationProcessStatus.STYLE_PLAN_GENERATING,
                ),
            )
            previous_blocks = {"intro": intro}
            plan_messages = self.prompt_builder.build_style_plan(
                character_json, general_block, previous_blocks
            )
            plan_call = await self._chat(
                self.settings.openrouter_model_profile,
                plan_messages,
                BlockStylePlan,
            )
            plan = BlockStylePlan.model_validate(orjson.loads(plan_call.content))
            plan.validate_for(general_block)
            await self.plans.create(
                GenerationStylePlanCreate(
                    generation_id=generation_id,
                    block=GenerationBlock.GENERAL,
                    status=GenerationStatus.COMPLETED,
                    used_model=self.settings.openrouter_model_profile,
                    prompt=self._dump(plan_messages),
                    token_usage=self._usage(plan_call),
                    result=plan.model_dump(mode="json"),
                )
            )
            await self.commit()
            self._progress(progress, "general_style_plan_generated", generation_id)

            await self.generations.update(
                generation_id,
                GenerationUpdate(
                    status=GenerationProcessStatus.CHARACTER_BLOCK_GENERATING
                ),
            )
            general_messages = self.prompt_builder.build_block(
                character_json, subject, general_block, plan, previous_blocks
            )
            general_call = await self._chat(
                self.settings.openrouter_model_report,
                general_messages,
                CharacterBlockResult,
            )
            general = CharacterBlockResult.model_validate(
                orjson.loads(general_call.content)
            )
            await self.blocks.create(
                GenerationCharacterBlockCreate(
                    generation_id=generation_id,
                    block=GenerationBlock.GENERAL,
                    status=GenerationStatus.COMPLETED,
                    used_model=self.settings.openrouter_model_report,
                    prompt=self._dump(general_messages),
                    token_usage=self._usage(general_call),
                    result=general.model_dump(mode="json"),
                )
            )
            await self.commit()
            self._progress(progress, "general_generated", generation_id)

            await self.generations.update(
                generation_id,
                GenerationUpdate(status=GenerationProcessStatus.COMPLETED),
            )
            await self.commit()
            return {
                "generation_id": str(generation_id),
                "chart_url": self.storage.presigned_url(chart_key),
                "blocks": {
                    "intro": intro.model_dump(mode="json"),
                    "general": general.model_dump(mode="json"),
                },
            }
        except Exception:
            await self.rollback()
            if generation_id is not None:
                await self.generations.update(
                    generation_id,
                    GenerationUpdate(status=GenerationProcessStatus.FAILED),
                )
                await self.commit()
            raise

    async def _chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        response_model: type[BaseModel],
    ) -> OpenRouterChatResult:
        return await self.openrouter.chat_completion(
            model=model,
            messages=messages,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "strict": True,
                    "schema": response_model.model_json_schema(),
                },
            },
        )

    @staticmethod
    def _usage(result: OpenRouterChatResult) -> dict[str, int | None]:
        return {
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        }

    @staticmethod
    def _dump(value: Any) -> str:
        return orjson.dumps(value).decode()

    @staticmethod
    def _progress(progress: Progress, stage: str, generation_id: UUID) -> None:
        progress({"stage": stage, "generation_id": str(generation_id)})
