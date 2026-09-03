from typing import TYPE_CHECKING
import uuid

from sqlalchemy import ForeignKey, Index, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.domain.users.models import Person


class AstroChart(Base):
    __tablename__ = "astro_charts"
    __table_args__ = (Index("astro_charts_person_id_idx", "person_id"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()")
    )
    person_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("persons.person_id", ondelete="CASCADE"),
        nullable=False,
    )
    natal_xml: Mapped[str] = mapped_column(Text, nullable=False)
    chart_svg: Mapped[str] = mapped_column(Text, nullable=False)

    person: Mapped["Person"] = relationship(back_populates="astro_charts")
