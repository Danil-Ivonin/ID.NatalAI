from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
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

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    user = await UserRepository(session).create_user(payload)
    await session.commit()
    return UserRead.model_validate(user)


@router.get("", response_model=list[UserRead])
async def list_users(
    session: AsyncSession = Depends(get_session),
) -> list[UserRead]:
    users = await UserRepository(session).list_users()
    return [UserRead.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    user = await UserRepository(session).get_user(user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return UserRead.model_validate(user)


@router.patch("/{user_id}", response_model=UserRead)
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_session),
) -> UserRead:
    user = await UserRepository(session).update_user(user_id, payload)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    await session.commit()
    return UserRead.model_validate(user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    if not await UserRepository(session).delete_user(user_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{user_id}/persons",
    response_model=PersonRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_person(
    user_id: UUID,
    payload: PersonCreate,
    session: AsyncSession = Depends(get_session),
) -> PersonRead:
    repository = UserRepository(session)
    if await repository.get_user(user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    person = await repository.create_person(user_id, payload)
    await session.commit()
    return PersonRead.model_validate(person)


@router.get("/{user_id}/persons", response_model=list[PersonRead])
async def list_persons(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> list[PersonRead]:
    repository = UserRepository(session)
    if await repository.get_user(user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    persons = await repository.list_persons(user_id)
    return [PersonRead.model_validate(person) for person in persons]


@router.get("/{user_id}/persons/{person_id}", response_model=PersonRead)
async def get_person(
    user_id: UUID,
    person_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> PersonRead:
    person = await UserRepository(session).get_person(user_id, person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person not found")
    return PersonRead.model_validate(person)


@router.patch("/{user_id}/persons/{person_id}", response_model=PersonRead)
async def update_person(
    user_id: UUID,
    person_id: UUID,
    payload: PersonUpdate,
    session: AsyncSession = Depends(get_session),
) -> PersonRead:
    person = await UserRepository(session).update_person(user_id, person_id, payload)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person not found")
    await session.commit()
    return PersonRead.model_validate(person)


@router.delete(
    "/{user_id}/persons/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_person(
    user_id: UUID,
    person_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> Response:
    if not await UserRepository(session).delete_person(user_id, person_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person not found")
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
