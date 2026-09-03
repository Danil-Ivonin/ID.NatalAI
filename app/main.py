from datetime import date, time
from fastapi import FastAPI

from app.api.v1 import users
from app.core.logging import configure_logging
from app.services.natal_chart_service import NatalChartService

configure_logging()

app = FastAPI(title="NatalAI Backend")
app.include_router(users.router, prefix="/api/v1")
app = FastAPI(title="NatalAI Backend")
app.include_router(generations.router, prefix="/api/v1")
app.include_router(personas.router, prefix="/api/v1")
app.include_router(prompt_templates.router, prefix="/api/v1")
