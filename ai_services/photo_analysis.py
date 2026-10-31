"""Photo analysis service for NagarWatch.

Orchestrates visual scene analysis, safety hazard detection, and category relevance assessment
for citizen-uploaded incident photos using Google Gemini vision capabilities.
Enforces strict policy that photos are purely advisory and never automatically reject reports
or definitively prove authenticity, date, location, or cause.
"""

import io
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_services.exceptions import (
    ClassificationValidationError,
    GeminiAPIError,
    GeminiConfigurationError,
    GeminiTimeoutError,
)
from ai_services.gemini_client import (
    GENAI_AVAILABLE,
    GeminiClientConfig,
    get_gemini_client,
    types,
)

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION = """You are the Photo Analysis Engine for NagarWatch, a Hyperlocal Community Safety Platform.
Analyze citizen-submitted incident photos objectively.

CRITICAL POLICY & VERIFICATION RULES:
1. Analyze only visible visual features in the image.
2. NEVER claim that an image proves the incident's authenticity, capture date, capture location, or root cause.
3. An image can only demonstrate whether visual conditions are CONSISTENT or INCONSISTENT with the claimed report.
4. Always identify visible limitations (e.g. poor lighting, blur, occlusion, limited field of view).
5. NEVER recommend rejecting or deleting a resident report based solely on an image.

You must respond ONLY with a valid JSON object matching this schema:
{
  "visible_description": "<1-3 sentences describing objectively what is visible in the photo>",
  "safety_hazards": ["<detected hazard 1>", "<detected hazard 2>"],
  "is_relevant_to_claim": <true | false | null>,
  "confidence": <float between 0.0 and 1.0>,
  "limitations": ["<uncertainty or visual limitation 1>", "<uncertainty or visual limitation 2>"],
  "explanation": "<2-4 sentences explaining the visual findings and category relevance without making definitive proof claims>"
}
DO NOT return markdown formatting or code fences. Return ONLY the raw JSON object.
"""


def build_photo_prompt(
    incident_description: Optional[str] = None,
    claimed_category: Optional[str] = None,
) -> str:
    """Format incident context into analysis prompt for Gemini vision."""
    parts = ["Analyze the attached incident photo for public safety triage."]
    if claimed_category and claimed_category.strip():
        parts.append(f"Claimed Category: {claimed_category.strip()}")
    if incident_description and incident_description.strip():
        parts.append(f"Resident Report: \"\"\"{incident_description.strip()}\"\"\"")
    parts.append(
        "Evaluate whether the visible scene shows conditions consistent with the claim. "
        "List any public safety hazards, limitations/uncertainties, and output the required JSON."
    )
    return "\n\n".join(parts)


def _clean_json_output(raw_text: str) -> str:
    """Strip optional markdown code block fences if returned by model."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


class RawPhotoAnalysisPayload(BaseModel):
    """Raw structured payload validated from Gemini vision output."""

    model_config = ConfigDict(extra="ignore")

    visible_description: str = Field(..., min_length=3)
    safety_hazards: List[str] = Field(default_factory=list)
    is_relevant_to_claim: Optional[bool] = Field(default=None)
    confidence: float = Field(..., ge=0.0, le=1.0)
    limitations: List[str] = Field(default_factory=list)
    explanation: str = Field(..., min_length=5)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Confidence score must be in range [0.0, 1.0], received {v}")
        return round(v, 4)


class PhotoAnalysisResult(BaseModel):
    """Complete, validated incident photo assessment returned to NagarWatch consumers.

    Enforces that photo analysis is purely advisory and never claims proof of
    authenticity, date, location, or cause, nor recommends automated rejection.
    """

    model_config = ConfigDict(frozen=True, use_enum_values=True)

    visible_description: str = Field(
        ...,
        description="Brief objective description of visible content in the image."
    )
    safety_hazards: List[str] = Field(
        default_factory=list,
        description="Detected objects, physical conditions, or risks relevant to public safety."
    )
    is_relevant_to_claim: Optional[bool] = Field(
        default=None,
        description="Whether the image appears visually relevant to the claimed category/description."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score (0.0 to 1.0) in the visual assessment."
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Identified uncertainties, image quality issues, or visual limitations."
    )
    explanation: str = Field(
        ...,
        description="Human-readable explanation of visual findings and relevance."
    )
    authenticity_disclaimer: str = Field(
        default=(
            "Image analysis is purely advisory and visual. It does NOT prove or verify "
            "the incident's authenticity, date, location, or cause."
        ),
        description="Mandatory disclaimer: photos never prove authenticity, date, location, or cause."
    )
    rejection_recommended: bool = Field(
        default=False,
        description="Always False: automated report rejection based on photos is strictly prohibited."
    )
    model_name: str = Field(
        default="gemini-2.5-flash",
        description="Model identifier used for analysis."
    )
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when evaluation occurred."
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert assessment to JSON-serializable dictionary."""
        return self.model_dump(mode="json")


class PhotoAnalyzer:
    """Visual triage and photo analysis engine for NagarWatch."""

    MAX_IMAGE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB limit
    SUPPORTED_MIME_TYPES: set[str] = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "image/heic",
        "image/heif",
    }

    def __init__(
        self,
        client: Optional[Any] = None,
        config: Optional[GeminiClientConfig] = None,
    ) -> None:
        """Initialize PhotoAnalyzer with optional client and config.

        Args:
            client: Optional pre-configured Gen AI client (enables mocking and DI).
            config: Optional GeminiClientConfig. Defaults to environment configuration.
        """
        self.config = config or GeminiClientConfig.from_env()
        self._client = client

    @property
    def client(self) -> Any:
        """Lazy-loaded or injected Google Gen AI client."""
        if self._client is None:
            self._client = get_gemini_client(self.config)
        return self._client

    @classmethod
    def detect_mime_type(cls, data: bytes, user_mime: Optional[str] = None) -> str:
        """Detect image MIME type from magic byte signatures with user fallback.

        Raises:
            ValueError: If image format is unsupported or unidentifiable.
        """
        if user_mime and user_mime.lower().strip() in cls.SUPPORTED_MIME_TYPES:
            return user_mime.lower().strip()

        if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
            return "image/jpeg"
        if len(data) >= 8 and data[:8] == b"\x89PNG\r\n\x1a\n":
            return "image/png"
        if len(data) >= 6 and data[:6] in (b"GIF87a", b"GIF89a"):
            return "image/gif"
        if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return "image/webp"
        if len(data) >= 12 and (
            b"ftypheic" in data[:20]
            or b"ftypheif" in data[:20]
            or b"ftypmif1" in data[:20]
        ):
            return "image/heic"

        raise ValueError(
            "Unsupported or unidentifiable image format. "
            "Allowed formats: JPEG, PNG, WEBP, GIF, HEIC."
        )

    def prepare_image_bytes(
        self,
        image: Union[bytes, bytearray, str, Path, Any],
        mime_type: Optional[str] = None,
    ) -> Tuple[bytes, str]:
        """Validate and prepare raw image bytes and detected MIME type.

        Raises:
            ValueError: If image is missing, empty, oversized, or an unsupported format.
            FileNotFoundError: If image is a string path that does not exist.
        """
        if image is None:
            raise ValueError("Image must be provided; received None.")

        data: bytes

        if isinstance(image, (str, Path)):
            path_str = str(image)
            if not os.path.exists(path_str):
                raise FileNotFoundError(f"Image file does not exist: {path_str}")
            with open(path_str, "rb") as f:
                data = f.read()
        elif hasattr(image, "read"):
            content = image.read()
            data = content if isinstance(content, bytes) else str(content).encode("utf-8")
            if mime_type is None and hasattr(image, "content_type"):
                mime_type = getattr(image, "content_type")
        elif isinstance(image, (bytes, bytearray)):
            data = bytes(image)
        else:
            raise ValueError(
                f"Unsupported image input type '{type(image).__name__}'. "
                "Expected bytes, file path, or file-like object."
            )

        if len(data) == 0:
            raise ValueError("Image data is empty (0 bytes).")

        if len(data) > self.MAX_IMAGE_SIZE_BYTES:
            raise ValueError(
                f"Image size ({len(data)} bytes) exceeds maximum allowable limit "
                f"of {self.MAX_IMAGE_SIZE_BYTES} bytes (10MB)."
            )

        detected_mime = self.detect_mime_type(data, user_mime=mime_type)
        return data, detected_mime

    def analyze_photo(
        self,
        image: Union[bytes, bytearray, str, Path, Any],
        incident_description: Optional[str] = None,
        claimed_category: Optional[str] = None,
        mime_type: Optional[str] = None,
    ) -> PhotoAnalysisResult:
        """Analyze an uploaded incident photo using Gemini vision capabilities.

        Args:
            image: Uploaded image as raw bytes, file path, or file-like object.
            incident_description: Optional resident description for context.
            claimed_category: Optional claimed incident category for relevance checking.
            mime_type: Optional explicit MIME type (e.g. 'image/jpeg').

        Returns:
            Structured PhotoAnalysisResult with visible description, hazards,
            relevance, confidence, limitations, and human explanation.

        Raises:
            ValueError: If image is missing, empty, oversized, or unsupported format.
            FileNotFoundError: If image file path does not exist.
            GeminiConfigurationError: If Gemini credentials/model are missing.
            GeminiTimeoutError: If the remote vision API request times out.
            GeminiAPIError: If Google Gemini encounters an upstream failure.
            ClassificationValidationError: If the model's response is empty or violates schema.
        """
        image_bytes, detected_mime = self.prepare_image_bytes(image, mime_type=mime_type)

        # Prepare multimodal payload for Google Gen AI SDK
        if types is not None:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=detected_mime)
        else:
            image_part = {"inline_data": {"mime_type": detected_mime, "data": image_bytes}}

        user_prompt = build_photo_prompt(
            incident_description=incident_description,
            claimed_category=claimed_category,
        )

        try:
            call_kwargs: dict[str, Any] = {
                "model": self.config.model_name,
                "contents": [image_part, user_prompt],
            }

            if types is not None:
                call_kwargs["config"] = types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    temperature=0.2,
                )

            response = self.client.models.generate_content(**call_kwargs)

        except TimeoutError as exc:
            raise GeminiTimeoutError(
                f"Gemini photo analysis timed out after {self.config.timeout_seconds}s.",
                details={"model": self.config.model_name, "error": str(exc)},
            ) from exc
        except Exception as exc:
            err_str = str(exc).lower()
            if "timeout" in err_str or "deadline exceeded" in err_str or "504" in err_str:
                raise GeminiTimeoutError(
                    f"Gemini photo analysis timed out: {exc}",
                    details={"model": self.config.model_name, "error": str(exc)},
                ) from exc
            if isinstance(exc, GeminiConfigurationError):
                raise
            raise GeminiAPIError(
                f"Google Gemini API error during photo analysis: {exc}",
                details={"model": self.config.model_name, "error": str(exc)},
            ) from exc

        # Extract and validate response text
        response_text = getattr(response, "text", None)
        if not response_text or not response_text.strip():
            raise ClassificationValidationError(
                "Gemini vision returned an empty or null response.",
                details={"model": self.config.model_name},
            )

        cleaned_json = _clean_json_output(response_text)

        try:
            payload = RawPhotoAnalysisPayload.model_validate_json(cleaned_json)
        except Exception as exc:
            raise ClassificationValidationError(
                f"Photo analysis response failed Pydantic schema validation: {exc}",
                details={"raw_output": cleaned_json, "error": str(exc)},
            ) from exc

        return PhotoAnalysisResult(
            visible_description=payload.visible_description,
            safety_hazards=payload.safety_hazards,
            is_relevant_to_claim=payload.is_relevant_to_claim,
            confidence=payload.confidence,
            limitations=payload.limitations,
            explanation=payload.explanation,
            authenticity_disclaimer=(
                "Image analysis is purely advisory and visual. It does NOT prove or verify "
                "the incident's authenticity, date, location, or cause."
            ),
            rejection_recommended=False,
            model_name=self.config.model_name,
            evaluated_at=datetime.now(timezone.utc),
        )


def analyze_photo(
    image: Union[bytes, bytearray, str, Path, Any],
    incident_description: Optional[str] = None,
    claimed_category: Optional[str] = None,
    mime_type: Optional[str] = None,
    client: Optional[Any] = None,
    config: Optional[GeminiClientConfig] = None,
) -> PhotoAnalysisResult:
    """Convenience function to analyze an incident photo."""
    analyzer = PhotoAnalyzer(client=client, config=config)
    return analyzer.analyze_photo(
        image=image,
        incident_description=incident_description,
        claimed_category=claimed_category,
        mime_type=mime_type,
    )
