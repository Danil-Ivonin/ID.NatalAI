from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domain.persona.schemas import PersonaCreate, PersonaRead, PersonaUpdate
from app.repositories.persona_repository import PersonaRepository

router = APIRouter(prefix="/personas", tags=["personas"])


@router.post("", response_model=PersonaRead, status_code=status.HTTP_201_CREATED)
async def create_persona(
    payload: PersonaCreate,
    session: AsyncSession = Depends(get_session),
) -> PersonaRead:
    repository = PersonaRepository(session)
    persona = await repository.create(payload)
    await session.commit()
    return PersonaRead.model_validate(persona)


@router.get("", response_model=list[PersonaRead])
async def list_personas(
    session: AsyncSession = Depends(get_session),
) -> list[PersonaRead]:
    repository = PersonaRepository(session)
    return [PersonaRead.model_validate(persona) for persona in await repository.list()]


@router.get("/{persona_id}", response_model=PersonaRead)
async def get_persona(
    persona_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> PersonaRead:
    repository = PersonaRepository(session)
    persona = await repository.get(persona_id)
    if persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found",
        )
    return PersonaRead.model_validate(persona)


@router.patch("/{persona_id}", response_model=PersonaRead)
async def update_persona(
    persona_id: UUID,
    payload: PersonaUpdate,
    session: AsyncSession = Depends(get_session),
) -> PersonaRead:
    repository = PersonaRepository(session)
    persona = await repository.update(persona_id, payload)
    if persona is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Persona not found",
        )
    await session.commit()
    return PersonaRead.model_validate(persona)
