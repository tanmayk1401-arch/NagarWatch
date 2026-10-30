"""Data schemas and type definitions for NagarWatch AI incident classification.

Uses Pydantic v2 for robust validation of classification inputs, Gemini model outputs,
and standardized incident assessment payloads.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict
from pydantic import BaseModel, ConfigDict, Field, field_validator


class IncidentCategory(str, Enum):
    """Standardized top-level incident categories for NagarWatch."""

    INFRASTRUCTURE = "Infrastructure"
    PUBLIC_SAFETY = "Public Safety"
    TRAFFIC_ROAD_HAZARD = "Traffic & Road Hazard"
    FIRE_ENVIRONMENTAL = "Fire & Environmental Hazard"
    SANITATION_HEALTH = "Sanitation & Health"
    NOISE_DISTURBANCE = "Noise & Public Nuisance"
    OTHER = "Other"


class IncidentSeverity(str, Enum):
    """Severity levels for triage and emergency escalation."""

    LOW = "Low"          # Minor issue, no threat to safety or property
    MEDIUM = "Medium"    # Moderate concern, needs attention within normal SLA
    HIGH = "High"        # Serious hazard, potential injury, needs urgent dispatch
    CRITICAL = "Critical"# Immediate danger to human life or public emergency


class LanguageDetection(str, Enum):
    """Detected language of the resident's incident report."""

    ENGLISH = "English"
    HINDI = "Hindi"
    HINGLISH = "Hinglish"
    OTHER = "Other"


class ClassificationPayload(BaseModel):
    """Raw structured payload returned by the Google Gemini model.

    Enforces strict typing and validation on all model-generated fields.
    """

    model_config = ConfigDict(extra="ignore", use_enum_values=True)

    category: IncidentCategory = Field(
        ...,
        description="Top-level incident domain category."
    )
    subcategory: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Specific granular incident type (e.g. 'Pothole', 'Streetlight Outage')."
    )
    severity: IncidentSeverity = Field(
        ...,
        description="Assessed severity level (Low, Medium, High, Critical)."
    )
    language: LanguageDetection = Field(
        ...,
        description="Identified primary language/dialect of the report."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Classification confidence score between 0.0 and 1.0."
    )
    explanation: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Concise rationale explaining the category and severity assessment."
    )

    @field_validator("subcategory", "explanation")
    @classmethod
    def clean_text_fields(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("Field cannot be empty or purely whitespace.")
        return trimmed

    @field_validator("confidence")
    @classmethod
    def validate_confidence_range(cls, value: float) -> float:
        if not (0.0 <= value <= 1.0):
            raise ValueError(f"Confidence score must be in range [0.0, 1.0], received {value}")
        return round(value, 4)


class IncidentClassificationResult(BaseModel):
    """Complete, validated incident assessment returned to NagarWatch consumers.

    Preserves the original resident report verbatim alongside model findings.
    """

    model_config = ConfigDict(frozen=True, use_enum_values=True)

    original_description: str = Field(
        ...,
        min_length=1,
        description="The untouched resident report text, preserved verbatim."
    )
    category: IncidentCategory = Field(
        ...,
        description="Assessed category."
    )
    subcategory: str = Field(
        ...,
        description="Granular incident subcategory."
    )
    severity: IncidentSeverity = Field(
        ...,
        description="Triage severity score."
    )
    language: LanguageDetection = Field(
        ...,
        description="Detected report language (English, Hindi, or Hinglish)."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Model confidence level."
    )
    explanation: str = Field(
        ...,
        description="Explanation of classification reasoning."
    )
    model_name: str = Field(
        default="gemini-2.5-flash",
        description="Name of the Gemini model used for inference."
    )
    source: str = Field(
        default="gemini",
        description="Origin of classification result ('gemini' or 'local_fallback')."
    )
    is_fallback: bool = Field(
        default=False,
        description="Indicates whether the result came from local deterministic fallback."
    )
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when evaluation occurred."
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the result to a serializable dictionary."""
        return self.model_dump(mode="json")
