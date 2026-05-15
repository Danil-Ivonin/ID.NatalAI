from enum import StrEnum


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class GenerationStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class GenerationStage(StrEnum):
    NATAL_CHART_BUILD = "natal_chart_build"
    ASTROLOGY_PROFILE_EXTRACTION = "astrology_profile_extraction"
    STYLED_REPORT_GENERATION = "styled_report_generation"
