from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exceptions import NotFoundError
from app.domain.generations.astro_charts.schemas import AstroChartRead
from app.domain.generations.generation_neutral.schemas import (
    GenerationNeutralRead,
)


def result_payload() -> dict:
    return {
        "blocks": [
            {
                "id": block_id,
                "title": block_id,
                "summary": "Сводка.",
                "facts": [],
                "hooks": [],
            }
            for block_id in ["general", "love", "work_money", "inner_demons"]
        ]
    }


class AstroService:
    def __init__(self) -> None:
        self.rows = {}

    async def create(self, data):
        row = AstroChartRead(
            id=uuid4(),
            person_id=data.person_id,
            natal_xml=data.natal_xml,
            chart_svg=f"https://s3.test/{data.chart_svg}",
        )
        self.rows[row.id] = row
        return row

    async def list(self, person_id):
        return [row for row in self.rows.values() if row.person_id == person_id]

    async def get(self, row_id):
        if row_id not in self.rows:
            raise NotFoundError("Astro chart not found")
        return self.rows[row_id]

    async def update(self, row_id, data):
        row = await self.get(row_id)
        values = row.model_dump()
        for field, value in data.model_dump(exclude_unset=True).items():
            values[field] = (
                f"https://s3.test/{value}" if field == "chart_svg" else value
            )
        updated = AstroChartRead(**values)
        self.rows[row_id] = updated
        return updated

    async def delete(self, row_id):
        await self.get(row_id)
        del self.rows[row_id]


class NeutralService:
    def __init__(self) -> None:
        self.rows = {}

    async def create(self, data):
        row = GenerationNeutralRead(id=uuid4(), **data.model_dump())
        self.rows[row.id] = row
        return row

    async def list(self, person_id):
        return [row for row in self.rows.values() if row.person_id == person_id]

    async def get(self, row_id):
        if row_id not in self.rows:
            raise NotFoundError("Neutral generation not found")
        return self.rows[row_id]

    async def update(self, row_id, data):
        row = await self.get(row_id)
        updated = row.model_copy(update=data.model_dump(exclude_unset=True))
        self.rows[row_id] = updated
        return updated

    async def delete(self, row_id):
        await self.get(row_id)
        del self.rows[row_id]


def client() -> TestClient:
    from app.api.v1 import generations
    from app.main import not_found_handler

    app = FastAPI()
    app.include_router(generations.router, prefix="/api/v1")
    app.add_exception_handler(NotFoundError, not_found_handler)
    astro_service = AstroService()
    neutral_service = NeutralService()
    app.dependency_overrides[generations.get_astro_chart_service] = (
        lambda: astro_service
    )
    app.dependency_overrides[generations.get_generation_neutral_service] = (
        lambda: neutral_service
    )
    return TestClient(app)


def test_astro_chart_api_crud_and_required_person_filter() -> None:
    api = client()
    person_id = uuid4()
    created = api.post(
        "/api/v1/generations/astro-charts",
        json={
            "person_id": str(person_id),
            "natal_xml": "<chart />",
            "chart_svg": "charts/a.svg",
        },
    )

    assert created.status_code == 201
    chart_id = created.json()["id"]
    assert api.get("/api/v1/generations/astro-charts").status_code == 422
    assert api.get(
        "/api/v1/generations/astro-charts", params={"person_id": str(person_id)}
    ).json() == [created.json()]
    assert api.get(f"/api/v1/generations/astro-charts/{chart_id}").json() == created.json()
    assert api.patch(
        f"/api/v1/generations/astro-charts/{chart_id}",
        json={"chart_svg": "charts/b.svg"},
    ).json()["chart_svg"].endswith("charts/b.svg")
    assert api.delete(f"/api/v1/generations/astro-charts/{chart_id}").status_code == 204
    assert api.get(f"/api/v1/generations/astro-charts/{chart_id}").status_code == 404


def test_generation_neutral_api_crud_and_required_person_filter() -> None:
    api = client()
    person_id = uuid4()
    payload = {
        "person_id": str(person_id),
        "used_model": "model",
        "prompt": "prompt",
        "token_usage": {"total_tokens": 42},
        "result": result_payload(),
    }
    created = api.post("/api/v1/generations/neutral", json=payload)

    assert created.status_code == 201
    generation_id = created.json()["id"]
    assert api.get("/api/v1/generations/neutral").status_code == 422
    assert api.get(
        "/api/v1/generations/neutral", params={"person_id": str(person_id)}
    ).json() == [created.json()]
    assert api.get(f"/api/v1/generations/neutral/{generation_id}").json() == created.json()
    assert api.patch(
        f"/api/v1/generations/neutral/{generation_id}", json={"prompt": "new"}
    ).json()["prompt"] == "new"
    assert api.delete(f"/api/v1/generations/neutral/{generation_id}").status_code == 204
    assert api.get(f"/api/v1/generations/neutral/{generation_id}").status_code == 404
