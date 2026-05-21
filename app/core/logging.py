import logging
import sys
from typing import Any

from app.core.config import get_settings


_STANDARD_LOG_RECORD_ATTRIBUTES = frozenset(
    logging.makeLogRecord({}).__dict__
) | {"asctime", "message"}


class ExtraFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_LOG_RECORD_ATTRIBUTES
            and not key.startswith("_")
            and value is not None
        }
        if not extras:
            return message
        fields = " ".join(
            f"{key}={self._format_value(value)}" for key, value in sorted(extras.items())
        )
        return f"{message} {fields}"

    @staticmethod
    def _format_value(value: Any) -> str:
        if isinstance(value, str):
            return repr(value) if any(char.isspace() for char in value) else value
        return str(value)


def configure_logging() -> None:
    settings = get_settings()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ExtraFormatter("%(asctime)s %(levelname)s [%(name)s] %(message)s")
    )
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        handlers=[handler],
        force=True,
    )
