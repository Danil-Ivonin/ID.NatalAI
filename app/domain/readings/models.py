import uuid
from typing import Any

from sqlalchemy import BigInteger, Identity, UUID, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NeutralGeneration(Base):
    __tablename__ = "neutral_generations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("uuidv7()"))
    reading: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
