"""Incident classification service for NagarWatch.

Orchestrates resident report triage across English, Hindi, and Hinglish using
the Google Gen AI SDK, enforcing schema validation and preserving raw reports verbatim.
Includes a deterministic local rule-based fallback when the remote API times out
or is temporarily unavailable.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional

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
from ai_services.prompts import SYSTEM_INSTRUCTION, build_user_prompt
from ai_services.schemas import (
    ClassificationPayload,
    IncidentCategory,
    IncidentClassificationResult,
    IncidentSeverity,
    LanguageDetection,
)

logger = logging.getLogger(__name__)


def detect_language(text: str) -> LanguageDetection:
    """Detect report language as English, Hindi (Devanagari), or Hinglish."""
    # 1. Hindi: Contains Devanagari Unicode characters (\u0900 - \u097F)
    if re.search(r"[\u0900-\u097F]", text):
        return LanguageDetection.HINDI

    # 2. Hinglish: Check for common Romanized Hindi/Urdu keywords
    tokens = set(re.findall(r"[a-zA-Z]+", text.lower()))
    hinglish_markers = {
        "me", "mai", "hai", "hain", "nahi", "nahin", "bohot", "bahut", "pichhle",
        "pichle", "din", "raat", "gali", "sadak", "paani", "pani", "aur", "ka",
        "ki", "ke", "ko", "par", "pe", "se", "yeh", "woh", "kuch", "kare",
        "karo", "raha", "rahi", "rahe", "tha", "thi", "the", "kharab", "gaddha",
        "gadha", "kooda", "kuda", "andhera", "bikers", "gir", "chuki", "chuka",
        "gaya", "gayi", "lagta", "wala", "wali", "chhedchhad", "chori", "hamla",
        "ped", "aag", "dhuan", "dhua", "bijli", "khamba", "tar", "shor", "ladai",
        "jhagda", "awaz", "bhai", "log", "kripya", "jaldi", "madad", "bheed"
    }
    strong_hinglish = {
        "gali", "sadak", "kharab", "andhera", "gaddha", "gadha", "kooda",
        "kuda", "pichhle", "pichle", "bohot", "bahut", "chhedchhad",
        "chori", "dhuan", "dhua", "jhagda", "bijli", "khamba"
    }
    if len(tokens.intersection(hinglish_markers)) >= 2 or any(token in strong_hinglish for token in tokens):
        return LanguageDetection.HINGLISH

    return LanguageDetection.ENGLISH


def classify_with_rule_fallback(original_description: str) -> IncidentClassificationResult:
    """Classify incident deterministically using local keyword and rule patterns.

    Used when Google Gemini times out or is temporarily unavailable.
    Preserves original resident description verbatim.
    Never attributes model_name or source to Gemini.
    """
    text_lower = original_description.lower()
    lang = detect_language(original_description)

    # Defaults
    category = IncidentCategory.OTHER
    subcategory = "Civic Issue"
    severity = IncidentSeverity.MEDIUM
    confidence = 0.85

    # 1. Fire & Environmental Hazard
    if any(k in text_lower for k in [
        "gas leak", "chemical leak", "gas smell", "cylinder leak", "गैस लीक", "सिलेंडर",
        "live wire", "exposed wire", "spark", "short circuit", "bijli ka tar", "बिजली का तार", "करंट",
        "fire", "burning", "burnt", "flame", "aag", "आग", "जल रहा",
        "smoke", "dhuan", "dhua", "धुआं", "धुआँ"
    ]):
        category = IncidentCategory.FIRE_ENVIRONMENTAL
        if any(k in text_lower for k in ["gas", "गैस", "cylinder"]):
            subcategory = "Gas Leak"
            severity = IncidentSeverity.CRITICAL
        elif any(k in text_lower for k in ["wire", "बिजली", "tar", "current", "spark", "short circuit", "करंट"]):
            subcategory = "Exposed Wire Hazard"
            severity = IncidentSeverity.CRITICAL
        elif any(k in text_lower for k in ["smoke", "dhuan", "dhua", "धुआं", "धुआँ"]):
            subcategory = "Smoke Hazard"
            severity = IncidentSeverity.HIGH
        else:
            subcategory = "Fire Hazard"
            severity = IncidentSeverity.CRITICAL

    # 2. Infrastructure (open manhole, water pipe burst, streetlights, drainage)
    elif any(k in text_lower for k in [
        "manhole", "man hole", "मैनहोल",
        "water pipe", "pipe burst", "pipeline", "पाइप फटा", "पानी का पाइप",
        "streetlight", "street light", "lamp post", "street lamp", "light kharab", "स्ट्रीट लाइट",
        "drain", "drainage", "sewer", "sewage", "gutter", "nali", "नाली", "सीवर", "गटर",
        "footpath", "sidewalk", "pavement", "फुटपाथ"
    ]):
        category = IncidentCategory.INFRASTRUCTURE
        if any(k in text_lower for k in ["manhole", "man hole", "मैनहोल"]):
            subcategory = "Open Manhole"
            severity = IncidentSeverity.CRITICAL
        elif any(k in text_lower for k in ["pipe", "पाइप", "burst", "water supply"]):
            subcategory = "Water Pipe Burst"
            severity = IncidentSeverity.HIGH
        elif any(k in text_lower for k in ["light", "lamp", "लाइट"]):
            subcategory = "Broken Streetlight"
            severity = IncidentSeverity.MEDIUM
        elif any(k in text_lower for k in ["drain", "sewer", "sewage", "gutter", "nali", "नाली", "सीवर"]):
            subcategory = "Blocked Drainage"
            severity = IncidentSeverity.MEDIUM
        elif any(k in text_lower for k in ["footpath", "sidewalk", "pavement", "फुटपाथ"]):
            subcategory = "Damaged Footpath"
            severity = IncidentSeverity.LOW
        else:
            subcategory = "Damaged Infrastructure"
            severity = IncidentSeverity.MEDIUM

    # 3. Traffic & Road Hazard
    elif any(k in text_lower for k in [
        "pothole", "gaddha", "gaddhe", "gadha", "गड्ढा", "गड्ढे",
        "fallen tree", "tree fallen", "ped gir", "पेड़ गिर",
        "traffic signal", "signal kharab", "traffic light", "सिग्नल",
        "accident", "collision", "skid", "crash", "bike fisal", "गिर चुकी", "गिर गया", "दुर्घटना",
        "traffic jam", "road block", "road hazard"
    ]):
        category = IncidentCategory.TRAFFIC_ROAD_HAZARD
        if any(k in text_lower for k in ["pothole", "gaddha", "gadha", "गड्ढा"]):
            subcategory = "Dangerous Pothole"
            severity = IncidentSeverity.HIGH
        elif any(k in text_lower for k in ["tree", "पेड़", "ped"]):
            subcategory = "Fallen Tree Obstruction"
            severity = IncidentSeverity.HIGH
        elif any(k in text_lower for k in ["signal", "सिग्नल"]):
            subcategory = "Traffic Signal Failure"
            severity = IncidentSeverity.HIGH
        elif any(k in text_lower for k in ["accident", "collision", "crash", "fisal", "गिर", "दुर्घटना"]):
            subcategory = "Road Collision Risk"
            severity = IncidentSeverity.HIGH
        else:
            subcategory = "Road Hazard"
            severity = IncidentSeverity.MEDIUM

    # 4. Sanitation & Health
    elif any(k in text_lower for k in [
        "garbage", "trash", "waste", "dump", "dustbin", "overflowing", "kachra", "kooda", "kuda", "कचरा", "कूड़ा",
        "dead animal", "carcass", "मरा हुआ जानवर",
        "mosquito", "dengue", "stagnant water", "मच्छर", "डेंगू", "ganda pani", "गंदा पानी",
        "foul smell", "stench", "badbu", "बदबू", "gandagi", "गंदगी"
    ]):
        category = IncidentCategory.SANITATION_HEALTH
        if any(k in text_lower for k in ["dead animal", "carcass", "मरा हुआ"]):
            subcategory = "Animal Carcass Removal"
            severity = IncidentSeverity.MEDIUM
        elif any(k in text_lower for k in ["mosquito", "dengue", "stagnant water", "मच्छर", "डेंगू"]):
            subcategory = "Stagnant Water Hazard"
            severity = IncidentSeverity.HIGH
        elif any(k in text_lower for k in ["garbage", "trash", "waste", "dump", "kachra", "kooda", "कचरा", "कूड़ा"]):
            subcategory = "Overflowing Garbage"
            severity = IncidentSeverity.MEDIUM
        else:
            subcategory = "Sanitation Concern"
            severity = IncidentSeverity.MEDIUM

    # 5. Public Safety
    elif any(k in text_lower for k in [
        "harassment", "harass", "stalking", "stalker", "chhedchhad", "छेड़छाड़",
        "theft", "thief", "stolen", "robbery", "robber", "burglary", "snatching", "chori", "chor", "चोरी", "चोर",
        "suspicious", "suspicious activity", "संदिग्ध",
        "assault", "violence", "weapon", "knife", "gun", "bandook", "chaku", "hamla", "हमला",
        "vandalism", "trespassing"
    ]):
        category = IncidentCategory.PUBLIC_SAFETY
        if any(k in text_lower for k in ["harass", "stalk", "chhedchhad", "छेड़छाड़"]):
            subcategory = "Street Harassment"
            severity = IncidentSeverity.HIGH
        elif any(k in text_lower for k in ["theft", "thief", "stolen", "robbery", "chori", "chor", "चोरी"]):
            subcategory = "Theft Incident"
            severity = IncidentSeverity.MEDIUM
        elif any(k in text_lower for k in ["suspicious", "संदिग्ध"]):
            subcategory = "Suspicious Activity"
            severity = IncidentSeverity.MEDIUM
        elif any(k in text_lower for k in ["assault", "violence", "weapon", "knife", "gun", "hamla", "हमला"]):
            subcategory = "Assault & Violent Threat"
            severity = IncidentSeverity.CRITICAL
        else:
            subcategory = "Public Safety Concern"
            severity = IncidentSeverity.MEDIUM

    # 6. Noise & Public Nuisance
    elif any(k in text_lower for k in [
        "loud music", "late night music", "music", "dj", "गाना", "डीजे",
        "brawl", "public fight", "screaming", "yelling", "ladai", "jhagda", "लड़ाई", "झगड़ा",
        "noise", "loudspeaker", "speaker", "शोर", "लाउडस्पीकर", "तेज आवाज", "shor"
    ]):
        category = IncidentCategory.NOISE_DISTURBANCE
        if any(k in text_lower for k in ["music", "dj", "गाना"]):
            subcategory = "Late Night Music"
            severity = IncidentSeverity.LOW
        elif any(k in text_lower for k in ["brawl", "fight", "ladai", "jhagda", "लड़ाई", "झगड़ा"]):
            subcategory = "Public Disturbance"
            severity = IncidentSeverity.MEDIUM
        else:
            subcategory = "Noise Disturbance"
            severity = IncidentSeverity.LOW

    # Special check: andhera / dark street light in Hinglish
    elif "andhera" in text_lower and ("street" in text_lower or "light" in text_lower or "gali" in text_lower):
        category = IncidentCategory.INFRASTRUCTURE
        subcategory = "Broken Streetlight"
        severity = IncidentSeverity.MEDIUM

    # Check for general severity escalations
    if any(k in text_lower for k in ["immediate danger", "life-safety", "falling in", "jaan ka khatra", "जान का खतरा", "blast", "explosion", "critical"]):
        severity = IncidentSeverity.CRITICAL
    elif severity == IncidentSeverity.LOW and any(k in text_lower for k in ["urgent", "severe", "flooded", "danger"]):
        severity = IncidentSeverity.HIGH

    explanation = (
        f"Deterministic rule-based fallback: classified as '{subcategory}' "
        f"({category.value}) with {severity.value} severity based on detected {lang.value} report keywords."
    )

    return IncidentClassificationResult(
        original_description=original_description,
        category=category,
        subcategory=subcategory,
        severity=severity,
        language=lang,
        confidence=confidence,
        explanation=explanation,
        model_name="rule-based-fallback",
        source="local_fallback",
        is_fallback=True,
        evaluated_at=datetime.now(timezone.utc),
    )


class IncidentClassifier:
    """Triage and classification engine for hyperlocal community incidents."""

    def __init__(
        self,
        client: Optional[Any] = None,
        config: Optional[GeminiClientConfig] = None,
        fallback_enabled: bool = True,
    ) -> None:
        """Initialize classifier with optional pre-configured client and configuration.

        Args:
            client: Optional pre-authenticated Gen AI client (enables dependency injection & mocking).
            config: Optional GeminiClientConfig. Defaults to environment-based configuration.
            fallback_enabled: Whether to invoke deterministic local fallback when Gemini times out
                              or is temporarily unavailable (defaults to True).
        """
        self.config = config or GeminiClientConfig.from_env()
        self._client = client
        self.fallback_enabled = fallback_enabled

    @property
    def client(self) -> Any:
        """Lazy-loaded or injected Google Gen AI client."""
        if self._client is None:
            self._client = get_gemini_client(self.config)
        return self._client

    def classify_incident(
        self,
        description: str,
        fallback_enabled: Optional[bool] = None,
    ) -> IncidentClassificationResult:
        """Classify a citizen incident report into category, severity, and metadata.

        Preserves the original report verbatim without altering formatting or words.
        Uses Google Gemini as the primary engine and deterministically falls back to a
        local rule-based classifier if Gemini times out or is temporarily unavailable.

        Args:
            description: Citizen report in English, Hindi, or Hinglish.
            fallback_enabled: Optional per-call override for fallback behavior.

        Returns:
            Validated IncidentClassificationResult with category, subcategory, severity,
            language, confidence, explanation, and untouched original description.

        Raises:
            ValueError: If description is not a valid non-empty string.
            GeminiConfigurationError: If API credentials or model settings are missing.
            GeminiTimeoutError: If the remote API call times out and fallback is disabled.
            GeminiAPIError: If Google Gemini encounters a non-transient API failure or fallback is disabled.
            ClassificationValidationError: If the model's output violates expected schema.
        """
        if not isinstance(description, str) or not description.strip():
            raise ValueError("Incident description must be a non-empty string.")

        # Requirement 5: Preserve original resident description verbatim
        original_description = description
        use_fallback = self.fallback_enabled if fallback_enabled is None else fallback_enabled

        # Build prompt payload
        user_content = build_user_prompt(original_description)

        try:
            # Configure request parameters for Google Gen AI SDK
            call_kwargs: dict[str, Any] = {
                "model": self.config.model_name,
                "contents": user_content,
            }

            if types is not None:
                call_kwargs["config"] = types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    temperature=0.1,  # Low temperature for deterministic classification
                )

            # Invoke remote Gemini model
            response = self.client.models.generate_content(**call_kwargs)

        except TimeoutError as exc:
            if use_fallback:
                logger.warning(
                    "Gemini API request timed out (%s). Using deterministic local fallback.",
                    exc,
                )
                return classify_with_rule_fallback(original_description)
            raise GeminiTimeoutError(
                f"Gemini API request timed out after {self.config.timeout_seconds}s.",
                details={"model": self.config.model_name, "error": str(exc)},
            ) from exc
        except Exception as exc:
            err_str = str(exc).lower()
            is_timeout = "timeout" in err_str or "deadline exceeded" in err_str or "504" in err_str
            is_unavailable = "unavailable" in err_str or "503" in err_str or "temporarily unavailable" in err_str

            if isinstance(exc, GeminiConfigurationError):
                raise

            if (is_timeout or is_unavailable) and use_fallback:
                logger.warning(
                    "Gemini API unavailable or timed out (%s). Using deterministic local fallback.",
                    exc,
                )
                return classify_with_rule_fallback(original_description)

            if is_timeout:
                raise GeminiTimeoutError(
                    f"Gemini API call timed out: {exc}",
                    details={"model": self.config.model_name, "error": str(exc)},
                ) from exc
            raise GeminiAPIError(
                f"Google Gemini API error during classification: {exc}",
                details={"model": self.config.model_name, "error": str(exc)},
            ) from exc

        # Extract and clean response text
        response_text = getattr(response, "text", None)
        if not response_text or not response_text.strip():
            raise ClassificationValidationError(
                "Gemini model returned an empty or null response.",
                details={"model": self.config.model_name},
            )

        cleaned_json = self._clean_json_output(response_text)

        # Validate structured output through Pydantic
        try:
            payload = ClassificationPayload.model_validate_json(cleaned_json)
        except Exception as exc:
            raise ClassificationValidationError(
                f"Model response failed Pydantic schema validation: {exc}",
                details={"raw_output": cleaned_json, "error": str(exc)},
            ) from exc

        # Construct and return immutable final result
        return IncidentClassificationResult(
            original_description=original_description,
            category=payload.category,
            subcategory=payload.subcategory,
            severity=payload.severity,
            language=payload.language,
            confidence=payload.confidence,
            explanation=payload.explanation,
            model_name=self.config.model_name,
            source="gemini",
            is_fallback=False,
            evaluated_at=datetime.now(timezone.utc),
        )

    @staticmethod
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
