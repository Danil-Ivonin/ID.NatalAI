from __future__ import annotations

from dataclasses import dataclass
import logging
from time import perf_counter
from typing import Any

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import Settings, get_settings
from app.core.exceptions import OpenRouterTemporaryError, ValidationFailure

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OpenRouterChatResult:
    content: str
    raw_response: dict[str, Any]
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int


class OpenRouterClient:
    def __init__(
        self,
        settings: Settings | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=self.settings.openrouter_base_url.rstrip("/"),
            timeout=60,
        )

    async def __aenter__(self) -> OpenRouterClient:
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def chat_completion(
        self,
        model: str,
        messages: list[dict[str, Any]],
        response_format: dict[str, Any] | None = None,
    ) -> OpenRouterChatResult:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self.settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }

        async for attempt in AsyncRetrying(
            retry=retry_if_exception_type(OpenRouterTemporaryError),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
            stop=stop_after_attempt(3),
            reraise=True,
        ):
            with attempt:
                started = perf_counter()
                try:
                    response = await self._client.post(
                        "/chat/completions",
                        json=payload,
                        headers=headers,
                    )
                except (httpx.TimeoutException, httpx.TransportError) as exc:
                    latency_ms = int((perf_counter() - started) * 1000)
                    logger.warning(
                        "openrouter request temporary transport error",
                        extra={
                            "model": model,
                            "latency_ms": latency_ms,
                            "attempt": attempt.retry_state.attempt_number,
                        },
                    )
                    raise OpenRouterTemporaryError(str(exc)) from exc

                latency_ms = int((perf_counter() - started) * 1000)
                logger.info(
                    "openrouter request completed",
                    extra={
                        "model": model,
                        "status_code": response.status_code,
                        "latency_ms": latency_ms,
                    },
                )

                if response.status_code >= 500:
                    raise OpenRouterTemporaryError(
                        f"OpenRouter returned {response.status_code}"
                    )
                if response.status_code >= 400:
                    raise ValidationFailure(
                        f"OpenRouter rejected request with {response.status_code}"
                    )

                raw_response = response.json()
                return self._parse_result(raw_response, latency_ms)

        raise OpenRouterTemporaryError("OpenRouter request failed")

    @staticmethod
    def _parse_result(
        raw_response: dict[str, Any], latency_ms: int
    ) -> OpenRouterChatResult:
        try:
            content = raw_response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValidationFailure("OpenRouter response missing message content") from exc

        usage = raw_response.get("usage") or {}
        return OpenRouterChatResult(
            content=content,
            raw_response=raw_response,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
            latency_ms=latency_ms,
        )
