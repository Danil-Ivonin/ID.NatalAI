from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.api.v1 import users
from app.core.exceptions import NotFoundError
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="NatalAI Backend")
app.include_router(users.router, prefix="/api/v1")


@app.exception_handler(NotFoundError)
async def not_found_handler(_: Request, error: NotFoundError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(error)},
    )
