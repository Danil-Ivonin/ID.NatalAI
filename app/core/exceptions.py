class NatalAIError(Exception):
    """Base exception for NatalAI application errors."""


class NotFoundError(NatalAIError):
    """Requested resource was not found."""


class ValidationFailure(NatalAIError):
    """Input or domain validation failed."""


class OpenRouterTemporaryError(NatalAIError):
    """OpenRouter request can be retried."""
