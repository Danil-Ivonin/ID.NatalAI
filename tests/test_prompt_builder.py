from app.domain.persona.context import PersonaContext
from app.services.prompt_builder import PromptBuilder


def _persona_context() -> PersonaContext:
    return PersonaContext(
        persona_name="Persona",
        persona_slug="persona",
        persona_description="Aggressive comic narrator.",
        voice_description="Sharp and theatrical.",
        humor_style="Roast comedy.",
        speech_patterns=["short punchlines", "direct address"],
        allowed_rules=["maximum intensity when requested"],
        forbidden_rules=["no protected-class hate"],
        allowed_quotes=["Tiny quote."],
        phrase_templates=["{name}, listen."],
        style_examples=["You are a walking calendar alert."],
    )


def test_build_astrology_profile_prompt_includes_subject_chart_and_json_rules() -> None:
    messages = PromptBuilder().build_astrology_profile_prompt(
        natal_xml="<chart>data</chart>",
        person_name="Irina",
        gender="female",
        template_content="SYSTEM TEMPLATE",
    )

    assert messages[0] == {"role": "system", "content": "SYSTEM TEMPLATE"}
    assert messages[1]["role"] == "user"
    user_prompt = messages[1]["content"]
    assert "Имя: Irina" in user_prompt
    assert "Гендер: female" in user_prompt
    assert "<chart>data</chart>" in user_prompt
    assert "strict JSON" in user_prompt
    assert "evidence" in user_prompt
    assert "do not invent chart data, placements, aspects, houses, or facts" in user_prompt
    assert "do not contradict the chart" in user_prompt
    assert "no markdown" in user_prompt
    assert "outside JSON" in user_prompt


def test_build_astrology_profile_prompt_renders_missing_subject_fields() -> None:
    user_prompt = PromptBuilder().build_astrology_profile_prompt(
        natal_xml="<chart />",
        person_name=None,
        gender=None,
        template_content="SYSTEM TEMPLATE",
    )[1]["content"]

    assert "Имя: не указано" in user_prompt
    assert "Гендер: не указан" in user_prompt


def test_build_styled_report_prompt_includes_inputs_schema_and_safety_rules() -> None:
    messages = PromptBuilder().build_styled_report_prompt(
        astrology_profile_json={"subject": {"person_name": "Irina"}, "traits": ["bold"]},
        persona_context=_persona_context(),
        person_name="Irina",
        gender="female",
        template_content="STYLE SYSTEM TEMPLATE",
    )

    assert messages[0] == {"role": "system", "content": "STYLE SYSTEM TEMPLATE"}
    assert messages[1]["role"] == "user"
    user_prompt = messages[1]["content"]
    assert "Имя: Irina" in user_prompt
    assert "Гендер: female" in user_prompt
    assert '"person_name": "Irina"' in user_prompt
    assert '"persona_slug": "persona"' in user_prompt
    assert "StyledNatalReport" in user_prompt
    assert "Anonymous" in user_prompt
    assert "do not invent astrology data" in user_prompt
    assert "no long copied quotes" in user_prompt
    assert "real-person impersonation disclaimer" in user_prompt
    assert "maximum-intensity roast/profanity/dark humor" in user_prompt
    assert "protected-class dehumanization" in user_prompt
    assert "real-world violence encouragement" in user_prompt


def test_build_styled_report_prompt_suppresses_anonymous_as_user_name_when_missing() -> None:
    user_prompt = PromptBuilder().build_styled_report_prompt(
        astrology_profile_json={"subject": {"person_name": None}},
        persona_context=_persona_context(),
        person_name=None,
        gender=None,
        template_content="STYLE SYSTEM TEMPLATE",
    )[1]["content"]

    assert "Имя: не указано" in user_prompt
    assert "Гендер: не указан" in user_prompt
    assert "Anonymous" not in user_prompt
