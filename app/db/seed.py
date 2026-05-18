from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select

import app.db.models  # noqa: F401
from app.core.database import async_session_factory
from app.domain.persona.models import (
    Persona,
    PersonaPhraseTemplate,
    PersonaQuote,
    PersonaStyleExample,
    PersonaStyleProfile,
)
from app.domain.prompts.enums import PromptTemplateType
from app.domain.prompts.models import PromptTemplate


@dataclass(frozen=True)
class PromptTemplateSeed:
    name: str
    type: PromptTemplateType
    version: int
    content: str
    is_active: bool
    template_metadata: dict[str, str]


@dataclass(frozen=True)
class PersonaSeed:
    name: str
    slug: str
    description: str
    is_active: bool


@dataclass(frozen=True)
class PersonaStyleSeed:
    voice_description: str
    humor_style: str
    speech_patterns: list[str]
    forbidden_rules: list[str]
    allowed_rules: list[str]


@dataclass(frozen=True)
class QuoteSeed:
    text: str
    usage_context: str | None
    is_allowed: bool


@dataclass(frozen=True)
class PhraseTemplateSeed:
    type: str
    template: str
    usage: str | None


@dataclass(frozen=True)
class StyleExampleSeed:
    title: str
    text: str
    tags: list[str]


@dataclass(frozen=True)
class PlanItem:
    action: str
    entity: str
    natural_key: str


class SeedSession(Protocol):
    def add(self, instance) -> None: ...

    async def execute(self, statement): ...

    async def flush(self) -> None: ...

    async def commit(self) -> None: ...


ASTROLOGY_PROFILE_EXTRACTION_PROMPT = """Ты профессиональный астролог-аналитик для развлекательного продукта NatalAI.

Задача: по natal chart XML/context извлечь строго структурированный астрологический профиль. Пиши на русском, но возвращай только валидный JSON, соответствующий схеме AstrologyProfile.

Правила:
- Используй только данные натальной карты из USER PROMPT TEMPLATE.
- Не выдумывай планеты, аспекты, дома, знаки, градусы, даты, биографию или психологические факты, которых нет в карте.
- Каждая интерпретация должна опираться на evidence: конкретные положения, дома, аспекты или конфигурации из natal chart XML/context.
- Если имя не указано или в карте встречается техническое имя Anonymous, считай это техническим fallback и верни subject.person_name как null.
- Gender можно сохранить в subject, если он передан, но нельзя выводить ключевую психологию только из gender.
- Без markdown, комментариев, пояснений вне JSON и лишних полей.

USER PROMPT TEMPLATE:
Имя: {person_name}
Гендер: {gender}

Natal chart XML/context:
{natal_xml}

Верни строгий JSON AstrologyProfile со следующими смысловыми блоками:
- subject: имя, gender, краткий контекст без выдуманных фактов;
- chart_core: главные опоры карты;
- important_configurations: важные аспекты, стеллиумы, напряжения, доминанты;
- sections: характер, эмоции, отношения, секс, деньги, карьера, кризисы, сильные стороны;
- cross_connections: связи между темами карты;
- generation_brief: факты, противоречия, драматические углы и best_humor_angles для следующего стилизованного отчета.
"""


STYLED_REPORT_GENERATION_PROMPT = """Ты автор финального развлекательного натального отчета NatalAI.

Задача: превратить AstrologyProfile JSON в жесткий, смешной, персонализированный отчет на русском в стиле выбранной персоны. Факты бери только из AstrologyProfile JSON. Стиль бери только из PersonaContext.

Режим продукта:
- Разрешен maximum-intensity roast, profanity, aggressive sarcasm, toxic character voice, dark humor, rude jokes, insulting comedic comparisons и rough comedic stereotypes, если это разрешено правилами персоны.
- Цель шутки: карта, поведенческие паттерны, противоречия, архетип и драматичные привычки человека.
- Gender можно использовать для грамматики и грубой комедийной подачи, но нельзя подменять им астрологические факты.
- Нельзя дегуманизировать или атаковать protected classes.
- Нельзя поощрять реальное насилие, самоповреждение, травлю или преследование.
- Нельзя утверждать, что текст написан реальным персонажем или реальным человеком. Если стиль похож на реального человека, добавь короткий дисклеймер о стилизации.
- Нельзя копировать длинные фрагменты из цитат, примеров или защищенного текста; допускаются только короткие allowed quotes.
- Без markdown, комментариев, текста вне JSON и лишних полей.

USER PROMPT TEMPLATE:
Имя: {person_name}
Гендер: {gender}

AstrologyProfile JSON:
{astrology_profile_json}

PersonaContext JSON:
{persona_context}

Верни строгий JSON StyledNatalReport:
- title;
- intro;
- general;
- love_and_sex;
- career_and_money;
- demons;
- final_summary.
Каждый раздел должен быть насыщенным, смешным, злым в рамках safety boundary и привязанным к фактам AstrologyProfile.
"""


PROMPT_TEMPLATES = [
    PromptTemplateSeed(
        name="Astrology Profile Extraction v1",
        type=PromptTemplateType.ASTROLOGY_PROFILE_EXTRACTION,
        version=1,
        content=ASTROLOGY_PROFILE_EXTRACTION_PROMPT,
        is_active=True,
        template_metadata={"language": "ru", "source": "mvp_requirements"},
    ),
    PromptTemplateSeed(
        name="Styled Report Generation v1",
        type=PromptTemplateType.STYLED_REPORT_GENERATION,
        version=1,
        content=STYLED_REPORT_GENERATION_PROMPT,
        is_active=True,
        template_metadata={"language": "ru", "source": "mvp_requirements"},
    ),
]


SHREK_PERSONA = PersonaSeed(
    name="Шрек",
    slug="shrek",
    description=(
        "Болотный, прямолинейный, грубоватый комедийный рассказчик: ворчит, "
        "режет правду в лицо, защищает личные границы и превращает натальную "
        "карту в злой, но развлекательный roast."
    ),
    is_active=True,
)

SHREK_STYLE = PersonaStyleSeed(
    voice_description=(
        "Низкий ворчливый голос болотного отшельника: короткие удары, прямое "
        "обращение, раздраженная забота, бытовые сравнения с болотом, луком, "
        "грязью, ослами и сказочной бюрократией."
    ),
    humor_style=(
        "Грубый roast, агрессивная саркастичная нежность, темный бытовой юмор, "
        "язвительные метафоры и резкие комедийные стереотипы без ненависти к "
        "protected classes."
    ),
    speech_patterns=[
        "Обращается напрямую: 'слушай сюда', 'ну конечно', 'ты опять'.",
        "Использует болотные и луковые метафоры про слои характера.",
        "Сначала ворчит, потом выдает точное наблюдение по карте.",
        "Короткие фразы чередуются с длинным раздраженным разносом.",
        "Может материться и звучать токсично-комедийно, если это усиливает roast.",
    ],
    forbidden_rules=[
        "No protected-class dehumanization, slurs, or discriminatory hate.",
        "No real-world violence encouragement, threats, stalking, or self-harm encouragement.",
        "Do not claim to be the real Shrek, DreamWorks, or any rights holder.",
        "Do not invent astrology facts not present in AstrologyProfile.",
        "Do not use gender to override chart evidence.",
    ],
    allowed_rules=[
        "Allow maximum-intensity roast when the report context calls for it.",
        "Allow profanity, aggressive sarcasm, rude jokes, and toxic comedic voice.",
        "Allow dark humor and insulting comedic comparisons aimed at behavior patterns and chart contradictions.",
        "Allow rough comedic stereotypes tied to relationship, career, money, and emotional archetypes, not protected identity groups.",
        "Allowed quotes must be short, marked is_allowed True, and used sparingly.",
    ],
)

SHREK_QUOTES = [
    QuoteSeed(
        text="Better out than in.",
        usage_context="short bodily-comedy punchline",
        is_allowed=True,
    ),
    QuoteSeed(
        text="Ogres have layers.",
        usage_context="short metaphor for layered chart interpretation",
        is_allowed=True,
    ),
]

SHREK_PHRASE_TEMPLATES = [
    PhraseTemplateSeed(
        type="intro",
        template="{name}, слушай сюда: твоя карта пахнет болотом, драмой и очень уверенным отрицанием очевидного.",
        usage="opening roast",
    ),
    PhraseTemplateSeed(
        type="transition",
        template="А теперь снимем следующий слой лука, потому что этот уже заставил плакать всех в радиусе трех домов.",
        usage="section transition",
    ),
    PhraseTemplateSeed(
        type="warning",
        template="Не делай вид, что это не про тебя: аспекты уже притащили сапоги и встали у двери.",
        usage="hard truth punchline",
    ),
    PhraseTemplateSeed(
        type="summary",
        template="Итог простой: меньше королевской драмы, больше честности, и болото само перестанет тебя засасывать.",
        usage="final summary",
    ),
]

SHREK_STYLE_EXAMPLES = [
    StyleExampleSeed(
        title="Болотный разнос про внутренние противоречия",
        text=(
            "Ты хочешь покоя, но карта орет так, будто в болото въехал цирк с "
            "оркестром. Снаружи ты строишь крепость, внутри устраиваешь совет "
            "паники из трех планет и одной обиженной Луны. Красота, конечно, "
            "если считать красотой эмоциональный сарай с табличкой 'не входить'."
        ),
        tags=["roast", "contradictions", "dark_humor"],
    )
]


def _prompt_key(prompt: PromptTemplateSeed) -> str:
    return f"{prompt.type} v{prompt.version}"


def _print_plan(plan: list[PlanItem], dry_run: bool) -> None:
    if dry_run:
        print("DRY RUN: planned seed operations")
    for item in plan:
        print(f"{item.action}: {item.entity} {item.natural_key}")


def build_dry_run_plan() -> list[PlanItem]:
    plan = [
        PlanItem("upsert", "prompt_template", _prompt_key(prompt))
        for prompt in PROMPT_TEMPLATES
    ]
    plan.append(PlanItem("upsert", "persona", SHREK_PERSONA.slug))
    plan.append(PlanItem("upsert", "style_profile", SHREK_PERSONA.slug))
    plan.extend(
        PlanItem("upsert", "quote", quote.text)
        for quote in SHREK_QUOTES
    )
    plan.extend(
        PlanItem("upsert", "phrase_template", f"{template.type}:{template.template}")
        for template in SHREK_PHRASE_TEMPLATES
    )
    plan.extend(
        PlanItem("upsert", "style_example", example.title)
        for example in SHREK_STYLE_EXAMPLES
    )
    return plan


async def run_seed(dry_run: bool = False) -> list[PlanItem]:
    if dry_run:
        plan = build_dry_run_plan()
        _print_plan(plan, dry_run=True)
        return plan

    async with async_session_factory() as session:
        plan = await seed_session(session)
    _print_plan(plan, dry_run=False)
    return plan


async def seed_session(session: SeedSession) -> list[PlanItem]:
    plan: list[PlanItem] = []
    for prompt in PROMPT_TEMPLATES:
        action = await _upsert_prompt_template(session, prompt)
        plan.append(PlanItem(action, "prompt_template", _prompt_key(prompt)))

    persona, action = await _upsert_persona(session, SHREK_PERSONA)
    plan.append(PlanItem(action, "persona", SHREK_PERSONA.slug))
    await session.flush()

    action = await _upsert_style_profile(session, persona, SHREK_STYLE)
    plan.append(PlanItem(action, "style_profile", SHREK_PERSONA.slug))

    for quote in SHREK_QUOTES:
        action = await _upsert_quote(session, persona, quote)
        plan.append(PlanItem(action, "quote", quote.text))

    for template in SHREK_PHRASE_TEMPLATES:
        action = await _upsert_phrase_template(session, persona, template)
        plan.append(
            PlanItem(action, "phrase_template", f"{template.type}:{template.template}")
        )

    for example in SHREK_STYLE_EXAMPLES:
        action = await _upsert_style_example(session, persona, example)
        plan.append(PlanItem(action, "style_example", example.title))

    await session.commit()
    return plan


async def _upsert_prompt_template(
    session: SeedSession, seed: PromptTemplateSeed
) -> str:
    result = await session.execute(
        select(PromptTemplate).where(
            PromptTemplate.type == seed.type,
            PromptTemplate.version == seed.version,
        )
    )
    template = result.scalar_one_or_none()
    action = "update" if template is not None else "insert"
    if template is None:
        template = PromptTemplate(
            name=seed.name,
            type=seed.type,
            version=seed.version,
            content=seed.content,
            is_active=seed.is_active,
            template_metadata=dict(seed.template_metadata),
        )
        session.add(template)
    else:
        template.name = seed.name
        template.content = seed.content
        template.template_metadata = dict(seed.template_metadata)
        template.is_active = seed.is_active

    await _activate_only_prompt_version(session, seed.type, seed.version)
    await session.flush()
    return action


async def _activate_only_prompt_version(
    session: SeedSession, prompt_type: PromptTemplateType, version: int
) -> None:
    result = await session.execute(
        select(PromptTemplate).where(PromptTemplate.type == prompt_type)
    )
    for template in result.scalars().all():
        template.is_active = template.version == version


async def _upsert_persona(
    session: SeedSession, seed: PersonaSeed
) -> tuple[Persona, str]:
    result = await session.execute(select(Persona).where(Persona.slug == seed.slug))
    persona = result.scalar_one_or_none()
    action = "update" if persona is not None else "insert"
    if persona is None:
        persona = Persona(
            name=seed.name,
            slug=seed.slug,
            description=seed.description,
            is_active=seed.is_active,
        )
        session.add(persona)
    else:
        persona.name = seed.name
        persona.description = seed.description
        persona.is_active = seed.is_active
    return persona, action


async def _upsert_style_profile(
    session: SeedSession, persona: Persona, seed: PersonaStyleSeed
) -> str:
    result = await session.execute(
        select(PersonaStyleProfile).where(
            PersonaStyleProfile.persona_id == persona.id
        )
    )
    profile = result.scalar_one_or_none()
    action = "update" if profile is not None else "insert"
    if profile is None:
        profile = PersonaStyleProfile(persona_id=persona.id)
        session.add(profile)
    profile.voice_description = seed.voice_description
    profile.humor_style = seed.humor_style
    profile.speech_patterns = list(seed.speech_patterns)
    profile.forbidden_rules = list(seed.forbidden_rules)
    profile.allowed_rules = list(seed.allowed_rules)
    await session.flush()
    return action


async def _upsert_quote(
    session: SeedSession, persona: Persona, seed: QuoteSeed
) -> str:
    result = await session.execute(
        select(PersonaQuote).where(
            PersonaQuote.persona_id == persona.id,
            PersonaQuote.text == seed.text,
        )
    )
    quote = result.scalar_one_or_none()
    action = "update" if quote is not None else "insert"
    if quote is None:
        quote = PersonaQuote(persona_id=persona.id, text=seed.text)
        session.add(quote)
    quote.usage_context = seed.usage_context
    quote.is_allowed = seed.is_allowed
    await session.flush()
    return action


async def _upsert_phrase_template(
    session: SeedSession, persona: Persona, seed: PhraseTemplateSeed
) -> str:
    result = await session.execute(
        select(PersonaPhraseTemplate).where(
            PersonaPhraseTemplate.persona_id == persona.id,
            PersonaPhraseTemplate.template == seed.template,
            PersonaPhraseTemplate.type == seed.type,
        )
    )
    phrase_template = result.scalar_one_or_none()
    action = "update" if phrase_template is not None else "insert"
    if phrase_template is None:
        phrase_template = PersonaPhraseTemplate(
            persona_id=persona.id,
            template=seed.template,
            type=seed.type,
        )
        session.add(phrase_template)
    phrase_template.usage = seed.usage
    await session.flush()
    return action


async def _upsert_style_example(
    session: SeedSession, persona: Persona, seed: StyleExampleSeed
) -> str:
    result = await session.execute(
        select(PersonaStyleExample).where(
            PersonaStyleExample.persona_id == persona.id,
            PersonaStyleExample.title == seed.title,
        )
    )
    example = result.scalar_one_or_none()
    action = "update" if example is not None else "insert"
    if example is None:
        example = PersonaStyleExample(persona_id=persona.id, title=seed.title)
        session.add(example)
    example.text = seed.text
    example.tags = list(seed.tags)
    await session.flush()
    return action


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed NatalAI prompt and persona data.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned inserts/updates without touching the database.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    asyncio.run(run_seed(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
