from typing import Annotated, Any
from uuid import UUID
from xml.etree import ElementTree

from pydantic import AfterValidator, BaseModel, ConfigDict, StringConstraints, model_validator


def _valid_xml(value: str) -> str:
    try:
        ElementTree.fromstring(value)
    except ElementTree.ParseError as error:
        raise ValueError("natal_xml must be valid XML") from error
    return value


NonBlankStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
XmlDocument = Annotated[NonBlankStr, AfterValidator(_valid_xml)]


class AstroChartCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    person_id: UUID
    natal_xml: XmlDocument
    chart_svg: NonBlankStr


class AstroChartUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    natal_xml: XmlDocument | None = None
    chart_svg: NonBlankStr | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_nulls(cls, data: Any) -> Any:
        if isinstance(data, dict) and any(value is None for value in data.values()):
            raise ValueError("updated fields cannot be null")
        return data


class AstroChartRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    person_id: UUID
    natal_xml: XmlDocument
    chart_svg: NonBlankStr
