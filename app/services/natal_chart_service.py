import logging
from dataclasses import dataclass
from datetime import date, time
from typing import Any

from kerykeion import AstrologicalSubjectFactory, to_context
from kerykeion.chart_data_factory import ChartDataFactory

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NatalChartResult:
    natal_xml: str
    chart_data_json: dict[str, Any] | None = None


class NatalChartService:
    def build_natal_chart(
        self,
        person_name: str | None,
        gender: str | None,
        birth_date: date,
        birth_time: time,
        lat: float,
        lng: float,
        timezone: str,
    ) -> NatalChartResult:
        chart_subject_name = person_name or "Anonymous"
        logger.info(
            "natal chart build started",
            extra={
                "chart_subject_name": chart_subject_name,
                "has_person_name": person_name is not None,
                "birth_date": birth_date.isoformat(),
                "birth_time": birth_time.strftime("%H:%M"),
                "birth_lat": lat,
                "birth_lng": lng,
                "birth_timezone": timezone,
                "gender_provided": gender is not None,
            },
        )
        subject = AstrologicalSubjectFactory.from_birth_data(
            chart_subject_name,
            birth_date.year,
            birth_date.month,
            birth_date.day,
            birth_time.hour,
            birth_time.minute,
            lng=lng,
            lat=lat,
            tz_str=timezone,
            online=False,
        )
        chart_data = ChartDataFactory.create_natal_chart_data(subject)
        natal_xml = to_context(chart_data)
        chart_data_json = self._to_json_dict(chart_data)

        logger.info(
            "natal chart build completed",
            extra={
                "chart_subject_name": chart_subject_name,
                "natal_xml_chars": len(natal_xml),
                "chart_data_available": chart_data_json is not None,
            },
        )

        return NatalChartResult(
            natal_xml=natal_xml,
            chart_data_json=chart_data_json,
        )

    @staticmethod
    def _to_json_dict(chart_data: Any) -> dict[str, Any] | None:
        if isinstance(chart_data, dict):
            return chart_data
        if hasattr(chart_data, "model_dump"):
            return chart_data.model_dump(mode="json")
        if hasattr(chart_data, "dict"):
            return chart_data.dict()
        return None
