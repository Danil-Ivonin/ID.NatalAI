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
                self._serialize_json(astrology_profile_json),
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
    def _serialize_json(value: Any) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, BaseModel):
            value = value.model_dump(mode="json")
        elif is_dataclass(value):
            value = asdict(value)

        return json.dumps(value, ensure_ascii=False, indent=2)
