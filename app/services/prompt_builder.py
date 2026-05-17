from dataclasses import asdict, is_dataclass
import json
from typing import Any

from pydantic import BaseModel


class PromptBuilder:
    def build_astrology_profile_prompt(
        self,
        natal_xml: str,
        person_name: str | None,
        gender: str | None,
        template_content: str,
    ) -> list[dict[str, str]]:
        user_prompt = "\n".join(
            [
                "Build an astrology profile from the natal chart context.",
                f"Имя: {person_name or 'не указано'}",
                f"Гендер: {gender or 'не указан'}",
                "",
                "Natal chart XML/context:",
                natal_xml,
                "",
                "Return strict JSON matching the AstrologyProfile schema.",
                "Every interpretation must include evidence from the natal chart data.",
                "do not invent chart data, placements, aspects, houses, or facts not present in natal_xml; do not contradict the chart.",
                *self._anonymous_profile_rules(person_name),
                "Use no markdown and no text outside JSON.",
            ]
        )
        return [
            {"role": "system", "content": template_content},
            {"role": "user", "content": user_prompt},
        ]

    def build_styled_report_prompt(
        self,
        astrology_profile_json: Any,
        persona_context: Any,
        person_name: str | None,
        gender: str | None,
        template_content: str,
    ) -> list[dict[str, str]]:
        rules = [
            "Return strict JSON matching the StyledNatalReport schema.",
            "do not invent astrology data; use only the supplied astrology profile.",
            "Use no markdown and no text outside JSON.",
            "Use no long copied quotes from persona examples or allowed quotes.",
            "Include a real-person impersonation disclaimer when styling resembles a real person.",
            "maximum-intensity roast/profanity/dark humor is allowed if persona rules allow it.",
            "hard stop: no protected-class dehumanization and no real-world violence encouragement.",
        ]
        if person_name:
            rules.append(
                "Anonymous suppression rule: never treat Anonymous as the user's actual name."
            )
        else:
            rules.append("Do not use placeholder or fallback names as the user's actual name.")

        user_prompt = "\n".join(
            [
                "Write the final styled natal report.",
                f"Имя: {person_name or 'не указано'}",
                f"Гендер: {gender or 'не указан'}",
                "",
                "AstrologyProfile JSON:",
                self._serialize_json(
                    astrology_profile_json,
                    sanitize_anonymous=person_name is None,
                ),
                "",
                "PersonaContext JSON:",
                self._serialize_json(persona_context),
                "",
                "\n".join(rules),
            ]
        )
        return [
            {"role": "system", "content": template_content},
            {"role": "user", "content": user_prompt},
        ]

    @staticmethod
    def _anonymous_profile_rules(person_name: str | None) -> list[str]:
        if person_name:
            return []
        return [
            "If XML/chart data contains name `Anonymous`, treat it only as technical kerykeion fallback.",
            "Do not use it as real user name.",
            "Return AstrologyProfile.subject.person_name as null.",
        ]

    @classmethod
    def _serialize_json(cls, value: Any, sanitize_anonymous: bool = False) -> str:
        if isinstance(value, str):
            if sanitize_anonymous:
                try:
                    value = json.loads(value)
                except json.JSONDecodeError:
                    return value.replace("Anonymous", "null")
            else:
                return value
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json")
        elif is_dataclass(value):
            value = asdict(value)

        if sanitize_anonymous:
            value = cls._sanitize_anonymous(value)

        return json.dumps(value, ensure_ascii=False, indent=2)

    @classmethod
    def _sanitize_anonymous(cls, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: cls._sanitize_anonymous(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._sanitize_anonymous(item) for item in value]
        if value == "Anonymous":
            return None
        return value
