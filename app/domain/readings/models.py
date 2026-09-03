from typing import Any

from sqlalchemy import BigInteger, Identity
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NeutralGeneration(Base):
    __tablename__ = "neutral_generations"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    reading: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
