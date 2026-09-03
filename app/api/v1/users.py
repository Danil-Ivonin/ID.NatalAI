from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.domain.users.schemas import (
    PersonCreate,
    PersonRead,
    PersonUpdate,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(UserRepository(session), session.commit)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    return UserRead.model_validate(await service.create_user(payload))


@router.get("", response_model=list[UserRead])
async def list_users(
    service: UserService = Depends(get_user_service),
) -> list[UserRead]:
    return [UserRead.model_validate(user) for user in await service.list_users()]


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    return UserRead.model_validate(await service.get_user(user_id))


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    service: UserService = Depends(get_user_service),
) -> UserRead:
    return UserRead.model_validate(await service.update_user(user_id, payload))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
) -> Response:
    await service.delete_user(user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{user_id}/persons",
    response_model=PersonRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_person(
    user_id: UUID,
    payload: PersonCreate,
    service: UserService = Depends(get_user_service),
) -> PersonRead:
    return PersonRead.model_validate(await service.create_person(user_id, payload))


@router.get("/{user_id}/persons", response_model=list[PersonRead])
async def list_persons(
    user_id: UUID,
    service: UserService = Depends(get_user_service),
) -> list[PersonRead]:
    return [
        PersonRead.model_validate(person)
        for person in await service.list_persons(user_id)
    ]


@router.get("/{user_id}/persons/{person_id}", response_model=PersonRead)
async def get_person(
    user_id: UUID,
    person_id: UUID,
    service: UserService = Depends(get_user_service),
) -> PersonRead:
    return PersonRead.model_validate(await service.get_person(user_id, person_id))


@router.patch("/{user_id}/persons/{person_id}", response_model=PersonRead)
async def update_person(
    user_id: UUID,
    person_id: UUID,
    payload: PersonUpdate,
    service: UserService = Depends(get_user_service),
) -> PersonRead:
    return PersonRead.model_validate(
        await service.update_person(user_id, person_id, payload)
    )


@router.delete(
    "/{user_id}/persons/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_person(
    user_id: UUID,
    person_id: UUID,
    service: UserService = Depends(get_user_service),
) -> Response:
    await service.delete_person(user_id, person_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
