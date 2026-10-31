"""Google Gen AI client wrapper and configuration manager.

Responsible for credential management, client instantiation, and parameterization
for the official Google Gen AI SDK (`google-genai`).
"""

import os
from dataclasses import dataclass, field
from typing import Any, Optional

from ai_services.exceptions import GeminiConfigurationError

# Attempt to load local .env if python-dotenv is installed
try:
    import dotenv
    dotenv.load_dotenv()
except ImportError:  # pragma: no cover
    pass

# Conditional import to allow mock testing and smooth developer onboarding
try:
    from google import genai
    from google.genai import types
    from google.genai.errors import APIError
    GENAI_AVAILABLE = True
except ImportError:  # pragma: no cover
    genai = None  # type: ignore
    types = None  # type: ignore
    APIError = Exception  # type: ignore
    GENAI_AVAILABLE = False


@dataclass(frozen=True)
class GeminiClientConfig:
    """Configuration container for Google Gemini API connections."""

    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY")
    )
    model_name: str = field(
        default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    )
    timeout_seconds: float = field(
        default_factory=lambda: float(os.getenv("GEMINI_TIMEOUT_SECONDS", "30.0"))
    )
    max_retries: int = field(
        default_factory=lambda: int(os.getenv("GEMINI_MAX_RETRIES", "3"))
    )

    @classmethod
    def from_env(cls) -> "GeminiClientConfig":
        """Load configuration strictly from environment variables."""
        return cls()

    def validate(self) -> None:
        """Validate presence of essential configuration parameters."""
        if not self.api_key or not self.api_key.strip():
            raise GeminiConfigurationError(
                "Gemini API key is missing. Set the 'GEMINI_API_KEY' environment "
                "variable or provide a valid key in your configuration."
            )
        if not self.model_name or not self.model_name.strip():
            raise GeminiConfigurationError(
                "Gemini model name cannot be empty. Set the 'GEMINI_MODEL' environment variable."
            )
        if self.timeout_seconds <= 0:
            raise GeminiConfigurationError(
                f"Timeout must be positive, received: {self.timeout_seconds}"
            )


def get_gemini_client(config: Optional[GeminiClientConfig] = None) -> Any:
    """Instantiate and return an authenticated Google Gen AI client.

    Args:
        config: Optional GeminiClientConfig. If omitted, loads from environment.

    Returns:
        google.genai.Client instance configured with credentials and timeouts.

    Raises:
        GeminiConfigurationError: If SDK is not installed or credentials are missing.
    """
    if not GENAI_AVAILABLE:
        raise GeminiConfigurationError(
            "The official 'google-genai' SDK is not installed in the active environment. "
            "Please run 'pip install -r requirements-ai.txt'."
        )

    cfg = config or GeminiClientConfig.from_env()
    cfg.validate()

    # Pass timeout via HttpOptions (timeout in milliseconds for google-genai)
    timeout_ms = int(cfg.timeout_seconds * 1000)
    http_options = types.HttpOptions(timeout=timeout_ms)

    return genai.Client(api_key=cfg.api_key, http_options=http_options)
