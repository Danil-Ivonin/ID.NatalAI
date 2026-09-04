from uuid import UUID

import anyio
from fastapi import APIRouter, Depends, Response, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, ConfigDict, ValidationError
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
from app.domain.generations.schemas import (
    GenerationCharacterBlockRead,
    GenerationCharacterBlockUpdate,
    GenerationCharacterBlockCreate,
    GenerationCreate,
    GenerationRead,
    GenerationStylePlanRead,
    GenerationStylePlanUpdate,
    GenerationStylePlanCreate,
    GenerationUpdate,
)
from app.repositories.character_repository import CharacterRepository
from app.repositories.generation_character_block_repository import (
    GenerationCharacterBlockRepository,
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
from app.services.generation_character_block_service import GenerationCharacterBlockService
from app.services.generation_service import GenerationService
from app.services.generation_style_plan_service import GenerationStylePlanService
from app.workers.tasks import generate_free

router = APIRouter(prefix="/generations", tags=["generations"])


class FreeGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_id: UUID
    character_id: UUID


def dispatch_free_generation(person_id: UUID, character_id: UUID):
    return generate_free.delay(str(person_id), str(character_id))


async def task_snapshot(task) -> tuple[str, object]:
    def read() -> tuple[str, object]:
        state = task.state
        return state, task.result if state == "SUCCESS" else task.info

    return await anyio.to_thread.run_sync(read)


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


def get_generation_character_block_service(
    session: AsyncSession = Depends(get_session),
) -> GenerationCharacterBlockService:
    return GenerationCharacterBlockService(
        GenerationCharacterBlockRepository(session),
        GenerationRepository(session),
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


@router.post(
    "/style-plans",
    response_model=GenerationStylePlanRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_generation_style_plan(
    payload: GenerationStylePlanCreate,
    service: GenerationStylePlanService = Depends(get_generation_style_plan_service),
) -> GenerationStylePlanRead:
    return await service.create(payload)


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


@router.post(
    "/character-blocks",
    response_model=GenerationCharacterBlockRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_generation_character_block(
    payload: GenerationCharacterBlockCreate,
    service: GenerationCharacterBlockService = Depends(
        get_generation_character_block_service
    ),
) -> GenerationCharacterBlockRead:
    return await service.create(payload)


@router.get(
    "/character-blocks", response_model=list[GenerationCharacterBlockRead]
)
async def list_generation_character_blocks(
    generation_id: UUID,
    service: GenerationCharacterBlockService = Depends(
        get_generation_character_block_service
    ),
) -> list[GenerationCharacterBlockRead]:
    return await service.list(generation_id)


@router.get(
    "/character-blocks/{block_id}", response_model=GenerationCharacterBlockRead
)
async def get_generation_character_block(
    block_id: UUID,
    service: GenerationCharacterBlockService = Depends(
        get_generation_character_block_service
    ),
) -> GenerationCharacterBlockRead:
    return await service.get(block_id)


@router.patch(
    "/character-blocks/{block_id}", response_model=GenerationCharacterBlockRead
)
async def update_generation_character_block(
    block_id: UUID,
    payload: GenerationCharacterBlockUpdate,
    service: GenerationCharacterBlockService = Depends(
        get_generation_character_block_service
    ),
) -> GenerationCharacterBlockRead:
    return await service.update(block_id, payload)


@router.delete(
    "/character-blocks/{block_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def delete_generation_character_block(
    block_id: UUID,
    service: GenerationCharacterBlockService = Depends(
        get_generation_character_block_service
    ),
) -> Response:
    await service.delete(block_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.websocket("/free")
async def free_generation_socket(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        try:
            payload = FreeGenerationRequest.model_validate(await websocket.receive_json())
        except (ValidationError, ValueError):
            await websocket.send_json({"type": "failed", "error": "invalid payload"})
            await websocket.close(code=1008)
            return

        task = dispatch_free_generation(payload.person_id, payload.character_id)
        await websocket.send_json({"type": "accepted", "task_id": task.id})
        sent_stages = 0
        while True:
            task_state, task_data = await task_snapshot(task)
            if isinstance(task_data, dict):
                stages = task_data.get("completed_stages", [])
                for event in stages[sent_stages:]:
                    await websocket.send_json({"type": "stage_completed", **event})
                sent_stages = len(stages)

            if task_state == "SUCCESS":
                result = dict(task_data)
                result.pop("completed_stages", None)
                await websocket.send_json({"type": "completed", **result})
                return
            if task_state == "FAILURE":
                await websocket.send_json({"type": "failed", "error": str(task_data)})
                return
            await anyio.sleep(0.25)
    except WebSocketDisconnect:
        return


@router.post("", response_model=GenerationRead, status_code=status.HTTP_201_CREATED)
async def create_generation(
    payload: GenerationCreate,
    service: GenerationService = Depends(get_generation_service),
) -> GenerationRead:
    return await service.create(payload)


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
