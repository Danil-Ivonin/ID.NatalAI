from datetime import date, time

from app.services.natal_chart_service import NatalChartService


def test_build_natal_chart_uses_kerykeion_birth_data_and_xml_context(monkeypatch) -> None:
    captured_birth_data = {}
    captured_chart_subject = {}
    captured_context_data = {}
    captured_drawer = {}

    class FakeSubjectFactory:
        @staticmethod
        def from_birth_data(name, year, month, day, hour, minute, **kwargs):
            captured_birth_data.update(
                {
                    "name": name,
                    "year": year,
                    "month": month,
                    "day": day,
                    "hour": hour,
                    "minute": minute,
                    **kwargs,
                }
            )
            return {"subject": name}

    class FakeChartDataFactory:
        @staticmethod
        def create_natal_chart_data(subject):
            captured_chart_subject["subject"] = subject
            return {"chart": subject}

    def fake_to_context(chart_data):
        captured_context_data["chart_data"] = chart_data
        return "<natal>xml</natal>"

    class FakeChartDrawer:
        def __init__(self, **kwargs):
            captured_drawer.update(kwargs)

        def generate_svg_string(self, **kwargs):
            captured_drawer["generate_svg_string_kwargs"] = kwargs
            return "<svg>chart</svg>"

    monkeypatch.setattr(
        "app.services.natal_chart_service.AstrologicalSubjectFactory",
        FakeSubjectFactory,
    )
    monkeypatch.setattr(
        "app.services.natal_chart_service.ChartDataFactory",
        FakeChartDataFactory,
    )
    monkeypatch.setattr("app.services.natal_chart_service.to_context", fake_to_context)
    monkeypatch.setattr("app.services.natal_chart_service.ChartDrawer", FakeChartDrawer)

    result = NatalChartService().build_natal_chart(
        person_name="Natasha",
        gender="female",
        birth_date=date(1992, 8, 14),
        birth_time=time(6, 45),
        lat=51.6608,
        lng=39.2003,
        timezone="Europe/Moscow",
        city="Воронеж",
        nation="RU",
    )

    assert result.natal_xml == "<natal>xml</natal>"
    assert result.chart_svg == "<svg>chart</svg>"
    assert captured_drawer == {
        "chart_data": {"chart": {"subject": "Natasha"}},
        "chart_language": "RU",
        "show_zodiac_background_ring": True,
        "style": "modern",
        "theme": "dark",
        "generate_svg_string_kwargs": {"remove_css_variables": True},
    }
    assert captured_birth_data == {
        "name": "Natasha",
        "year": 1992,
        "month": 8,
        "day": 14,
        "hour": 6,
        "minute": 45,
        "lng": 39.2003,
        "lat": 51.6608,
        "tz_str": "Europe/Moscow",
        "city": "Воронеж",
        "nation": "RU",
        "online": False,
    }
    assert "gender" not in captured_birth_data
    assert captured_chart_subject == {"subject": {"subject": "Natasha"}}
    assert captured_context_data == {"chart_data": {"chart": {"subject": "Natasha"}}}


def test_build_natal_chart_uses_anonymous_fallback_for_missing_name(monkeypatch) -> None:
    captured_birth_data = {}

    class FakeSubjectFactory:
        @staticmethod
        def from_birth_data(name, year, month, day, hour, minute, **kwargs):
            captured_birth_data["name"] = name
            return object()

    class FakeChartDataFactory:
        @staticmethod
        def create_natal_chart_data(subject):
            return {"chart": "data"}

    monkeypatch.setattr(
        "app.services.natal_chart_service.AstrologicalSubjectFactory",
        FakeSubjectFactory,
    )
    monkeypatch.setattr(
        "app.services.natal_chart_service.ChartDataFactory",
        FakeChartDataFactory,
    )
    monkeypatch.setattr(
        "app.services.natal_chart_service.to_context",
        lambda chart_data: "<anonymous />",
    )
    monkeypatch.setattr(
        "app.services.natal_chart_service.ChartDrawer",
        lambda **kwargs: type(
            "FakeChartDrawer",
            (),
            {
                "generate_svg_string": lambda self, **kwargs: (
                    "<svg>anonymous</svg>"
                )
            },
        )(),
    )

    result = NatalChartService().build_natal_chart(
        person_name=None,
        gender=None,
        birth_date=date(1991, 1, 2),
        birth_time=time(3, 4),
        lat=51.6608,
        lng=39.2003,
        timezone="Europe/Moscow",
        city="Воронеж",
        nation="RU",
    )

    assert captured_birth_data["name"] == "Anonymous"
    assert result.natal_xml == "<anonymous />"
    assert result.chart_svg == "<svg>anonymous</svg>"
