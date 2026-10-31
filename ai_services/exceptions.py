"""Custom exception hierarchy for NagarWatch AI Services.

Provides granular error handling for configuration errors, network/API timeouts,
upstream Gemini API errors, and schema validation failures.
"""

from typing import Any, Dict, Optional


class AIServiceError(Exception):
    """Base exception for all NagarWatch AI service failures."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(message={self.message!r}, details={self.details!r})"


class GeminiConfigurationError(AIServiceError):
    """Raised when configuration, credentials, or environment variables are missing/invalid."""
    pass


class GeminiAPIError(AIServiceError):
    """Raised when an upstream Google Gemini API call fails (network, rate-limit, quotas)."""
    pass


class GeminiTimeoutError(GeminiAPIError):
    """Raised when an API request to Google Gemini exceeds the configured timeout."""
    pass


class ClassificationValidationError(AIServiceError):
    """Raised when model response output fails Pydantic schema validation or cannot be parsed."""
    pass
