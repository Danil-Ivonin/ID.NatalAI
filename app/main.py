from fastapi import FastAPI

from app.api.v1 import generations, personas, prompt_templates
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(title="NatalAI Backend")
app.include_router(generations.router, prefix="/api/v1")
app.include_router(personas.router, prefix="/api/v1")
app.include_router(prompt_templates.router, prefix="/api/v1")
