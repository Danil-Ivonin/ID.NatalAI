from pydantic import BaseModel, ConfigDict


class StrictSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlacementMeaning(StrictSchema):
    name: str
    meaning: str
    evidence: list[str]


class Trait(StrictSchema):
    name: str
    description: str
    evidence: list[str]


class Pattern(StrictSchema):
    name: str
    description: str
    evidence: list[str]


class StrengthWeakness(StrictSchema):
    strength: str
    weakness: str
    evidence: list[str]


class BigThree(StrictSchema):
    sun: PlacementMeaning
    moon: PlacementMeaning
    ascendant: PlacementMeaning
    summary: str
    evidence: list[str]


class Dominants(StrictSchema):
    planets: list[str]
    signs: list[str]
    elements: list[str]
    modalities: list[str]
    summary: str
    evidence: list[str]


class MainLifePattern(Pattern):
    pass


class ChartCore(StrictSchema):
    big_three: BigThree
    dominants: Dominants
    main_life_pattern: MainLifePattern


class ImportantConfiguration(StrictSchema):
    name: str
    description: str
    impact: str
    evidence: list[str]


class RahuKetu(StrictSchema):
    rahu: str
    ketu: str
    evidence: list[str]


class LoveBlock(StrictSchema):
    description: str
    blocks: list[str]
    evidence: list[str]


class SexBlock(StrictSchema):
    description: str
    blocks: list[str]
    evidence: list[str]


class CareerBlock(StrictSchema):
    description: str
    best_paths: list[str]
    risks: list[str]
    evidence: list[str]


class MoneyBlock(StrictSchema):
    description: str
    earning_patterns: list[str]
    risks: list[str]
    evidence: list[str]


class LilithBlock(StrictSchema):
    description: str
    triggers: list[str]
    evidence: list[str]


class GeneralSection(StrictSchema):
    traits: list[Trait]
    patterns: list[Pattern]
    strengths_weaknesses: list[StrengthWeakness]
    summary: str
    evidence: list[str]


class LoveAndSexSection(StrictSchema):
    rahu_ketu: RahuKetu
    love: LoveBlock
    sex: SexBlock
    summary: str
    evidence: list[str]


class CareerAndMoneySection(StrictSchema):
    career: CareerBlock
    money: MoneyBlock
    summary: str
    evidence: list[str]


class DemonsSection(StrictSchema):
    lilith: LilithBlock
    inner_demons: list[Pattern]
    self_sabotage: list[Pattern]
    summary: str
    evidence: list[str]


class Sections(StrictSchema):
    general: GeneralSection
    love_and_sex: LoveAndSexSection
    career_and_money: CareerAndMoneySection
    demons: DemonsSection


class Subject(StrictSchema):
    person_name: str | None
    gender: str | None
    birth_date: str
    birth_time: str
    birth_place: str


class GenerationBrief(StrictSchema):
    core_character: str
    main_conflict: str
    main_strength: str
    main_weakness: str
    best_humor_angles: list[str]
    sensitive_topics_to_avoid: list[str]
    recommended_tone: str


class AstrologyProfile(StrictSchema):
    subject: Subject
    chart_core: ChartCore
    important_configurations: list[ImportantConfiguration]
    sections: Sections
    cross_connections: list[Pattern]
    generation_brief: GenerationBrief


class ReportSection(StrictSchema):
    title: str
    text: str


class StyledNatalReport(StrictSchema):
    title: str
    intro: ReportSection
    general: ReportSection
    love_and_sex: ReportSection
    career_and_money: ReportSection
    demons: ReportSection
    final_summary: ReportSection
