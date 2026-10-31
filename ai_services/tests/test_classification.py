"""Comprehensive mocked unit tests for NagarWatch AI incident classification.

Verifies multilingual support (English, Hindi, Hinglish), schema validation,
verbatim original description preservation, and error/timeout handling without
requiring a real Gemini API key or external network connectivity.
"""

import json
from unittest.mock import MagicMock

try:
    import pytest
except ImportError:  # pragma: no cover
    import contextlib

    class _PytestFallback:
        @staticmethod
        @contextlib.contextmanager
        def raises(expected_exception, match=None):
            try:
                yield
            except expected_exception as exc:
                if match and match not in str(exc):
                    raise AssertionError(f"Pattern '{match}' not found in exception message: '{exc}'")
            else:
                raise AssertionError(f"Expected exception {expected_exception} was not raised")

    pytest = _PytestFallback()  # type: ignore

from ai_services.classification import IncidentClassifier
from ai_services.exceptions import (
    ClassificationValidationError,
    GeminiAPIError,
    GeminiConfigurationError,
    GeminiTimeoutError,
)
from ai_services.gemini_client import GeminiClientConfig
from ai_services.schemas import (
    IncidentCategory,
    IncidentSeverity,
    LanguageDetection,
)


def create_mock_client(response_text: str):
    """Helper to create a mocked Google Gen AI client returning specified text."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


# ==============================================================================
# Multilingual Classification Tests (English, Hindi, Hinglish)
# ==============================================================================

def test_english_incident_classification():
    """Test classification of an English citizen report."""
    input_text = "Open manhole on Main Street near the bus stop. Immediate danger of someone falling in."
    mock_payload = {
        "category": "Infrastructure",
        "subcategory": "Open Manhole",
        "severity": "Critical",
        "language": "English",
        "confidence": 0.98,
        "explanation": "An open manhole poses an immediate life-safety hazard for pedestrians and vehicular traffic."
    }
    client = create_mock_client(json.dumps(mock_payload))
    classifier = IncidentClassifier(client=client)

    result = classifier.classify_incident(input_text)

    assert result.original_description == input_text
    assert result.category == IncidentCategory.INFRASTRUCTURE
    assert result.subcategory == "Open Manhole"
    assert result.severity == IncidentSeverity.CRITICAL
    assert result.language == LanguageDetection.ENGLISH
    assert result.confidence == 0.98
    assert "life-safety hazard" in result.explanation


def test_hindi_incident_classification():
    """Test classification of a Hindi (Devanagari) citizen report."""
    input_text = "मुख्य सड़क पर गहरा गड्ढा है, पानी भरने की वजह से कई बाइक फिसल कर गिर चुकी हैं।"
    mock_payload = {
        "category": "Traffic & Road Hazard",
        "subcategory": "Dangerous Pothole",
        "severity": "High",
        "language": "Hindi",
        "confidence": 0.95,
        "explanation": "सड़क पर गहरा गड्ढा वाहनों के लिए बड़ा खतरा पैदा कर रहा है और दुर्घटनाएं हो रही हैं।"
    }
    client = create_mock_client(json.dumps(mock_payload))
    classifier = IncidentClassifier(client=client)

    result = classifier.classify_incident(input_text)

    assert result.original_description == input_text
    assert result.category == IncidentCategory.TRAFFIC_ROAD_HAZARD
    assert result.subcategory == "Dangerous Pothole"
    assert result.severity == IncidentSeverity.HIGH
    assert result.language == LanguageDetection.HINDI
    assert result.confidence == 0.95
    assert len(result.explanation) > 10


def test_hinglish_incident_classification():
    """Test classification of a Hinglish (Romanized Hindi) citizen report."""
    input_text = "Gali no 4 me pichhle 5 din se street light kharab hai, raat ko bohot andhera rehta hai aur safe nahi lagta."
    mock_payload = {
        "category": "Infrastructure",
        "subcategory": "Broken Streetlight",
        "severity": "Medium",
        "language": "Hinglish",
        "confidence": 0.93,
        "explanation": "Outage of streetlights causes poor visibility and compromises local pedestrian safety at night."
    }
    client = create_mock_client(json.dumps(mock_payload))
    classifier = IncidentClassifier(client=client)

    result = classifier.classify_incident(input_text)

    assert result.original_description == input_text
    assert result.category == IncidentCategory.INFRASTRUCTURE
    assert result.subcategory == "Broken Streetlight"
    assert result.severity == IncidentSeverity.MEDIUM
    assert result.language == LanguageDetection.HINGLISH
    assert result.confidence == 0.93


# ==============================================================================
# Data Preservation & Output Formatting Tests
# ==============================================================================

def test_preserve_original_description_verbatim():
    """Ensure the original citizen report is preserved character-for-character."""
    raw_resident_input = "  URGENT!! Water pipe burst @ Sector 14, Plot #45... Road is totally flooded!  "
    mock_payload = {
        "category": "Infrastructure",
        "subcategory": "Water Pipe Burst",
        "severity": "High",
        "language": "English",
        "confidence": 0.96,
        "explanation": "A major water main burst causing street flooding and utility waste."
    }
    client = create_mock_client(json.dumps(mock_payload))
    classifier = IncidentClassifier(client=client)

    result = classifier.classify_incident(raw_resident_input)

    # Must preserve exact whitespace, punctuation, and case
    assert result.original_description == raw_resident_input


def test_markdown_code_fence_cleaning():
    """Ensure model output wrapped in markdown code fences is cleaned and parsed."""
    input_text = "Garbage piled up on corner of 5th cross road for three days."
    wrapped_json = """```json
{
  "category": "Sanitation & Health",
  "subcategory": "Overflowing Garbage",
  "severity": "Medium",
  "language": "English",
  "confidence": 0.91,
  "explanation": "Accumulated municipal waste poses hygiene and sanitation concerns."
}
```"""
    client = create_mock_client(wrapped_json)
    classifier = IncidentClassifier(client=client)

    result = classifier.classify_incident(input_text)
    assert result.category == IncidentCategory.SANITATION_HEALTH
    assert result.subcategory == "Overflowing Garbage"


def test_to_dict_serialization():
    """Ensure result converts cleanly into a JSON-serializable dictionary."""
    input_text = "Loud music playing at 2 AM near residential apartment."
    mock_payload = {
        "category": "Noise & Public Nuisance",
        "subcategory": "Late Night Music",
        "severity": "Low",
        "language": "English",
        "confidence": 0.88,
        "explanation": "Late night residential noise violation."
    }
    client = create_mock_client(json.dumps(mock_payload))
    classifier = IncidentClassifier(client=client)

    result = classifier.classify_incident(input_text)
    data = result.to_dict()

    assert isinstance(data, dict)
    assert data["category"] == "Noise & Public Nuisance"
    assert data["severity"] == "Low"
    assert data["language"] == "English"
    assert data["confidence"] == 0.88
    assert data["original_description"] == input_text
    assert "evaluated_at" in data


# ==============================================================================
# Error Handling & Edge Case Tests
# ==============================================================================

def test_empty_description_raises_value_error():
    """Passing an empty or whitespace-only description must raise ValueError."""
    classifier = IncidentClassifier(client=MagicMock())

    with pytest.raises(ValueError, match="non-empty string"):
        classifier.classify_incident("")

    with pytest.raises(ValueError, match="non-empty string"):
        classifier.classify_incident("    \n\t  ")


def test_missing_api_key_raises_configuration_error():
    """Missing API key must raise GeminiConfigurationError upon validation."""
    config = GeminiClientConfig(api_key="")
    with pytest.raises(GeminiConfigurationError, match="API key is missing"):
        config.validate()


def test_api_timeout_raises_gemini_timeout_error():
    """Network or API timeouts must be wrapped into GeminiTimeoutError when fallback is disabled."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("Connection timed out after 30000ms")
    classifier = IncidentClassifier(client=mock_client, fallback_enabled=False)

    with pytest.raises(GeminiTimeoutError, match="timed out"):
        classifier.classify_incident("Smoke coming from vacant plot")


def test_deadline_exceeded_raises_gemini_timeout_error():
    """Deadline exceeded exception must be classified as GeminiTimeoutError when fallback is disabled."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("504 Gateway Timeout: Deadline Exceeded")
    classifier = IncidentClassifier(client=mock_client, fallback_enabled=False)

    with pytest.raises(GeminiTimeoutError, match="timed out"):
        classifier.classify_incident("Smoke coming from vacant plot")


def test_upstream_api_failure_raises_gemini_api_error():
    """General upstream API or quota failures must raise GeminiAPIError."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("429 Resource has been exhausted (e.g. check quota).")
    classifier = IncidentClassifier(client=mock_client)

    with pytest.raises(GeminiAPIError, match="Google Gemini API error"):
        classifier.classify_incident("Suspicious activity reported near bank ATM")


def test_invalid_json_raises_validation_error():
    """Unparseable model output must raise ClassificationValidationError."""
    invalid_raw_text = "I apologize, but I cannot process this incident report right now."
    client = create_mock_client(invalid_raw_text)
    classifier = IncidentClassifier(client=client)

    with pytest.raises(ClassificationValidationError, match="schema validation"):
        classifier.classify_incident("Broken street sign on 10th main")


def test_invalid_schema_data_raises_validation_error():
    """Model output with out-of-range confidence (>1.0) must fail validation."""
    invalid_payload = {
        "category": "Infrastructure",
        "subcategory": "Damaged Road",
        "severity": "Low",
        "language": "English",
        "confidence": 1.95,  # Out of range!
        "explanation": "Valid explanation."
    }
    client = create_mock_client(json.dumps(invalid_payload))
    classifier = IncidentClassifier(client=client)

    with pytest.raises(ClassificationValidationError):
        classifier.classify_incident("Minor crack on sidewalk")


def test_empty_model_response_raises_validation_error():
    """Empty or null model response must raise ClassificationValidationError."""
    client = create_mock_client("   ")
    classifier = IncidentClassifier(client=client)

    with pytest.raises(ClassificationValidationError, match="empty or null"):
        classifier.classify_incident("Water leakage near society gate")


# ==============================================================================
# Deterministic Fallback Tests (Timeout & Temporary Unavailability)
# ==============================================================================

def test_timeout_triggers_deterministic_fallback():
    """Network timeout invokes deterministic fallback returning valid result schema."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("Connection timed out after 30000ms")
    classifier = IncidentClassifier(client=mock_client)

    result = classifier.classify_incident("Smoke coming from vacant plot")

    assert result.is_fallback is True
    assert result.source == "local_fallback"
    assert result.model_name == "rule-based-fallback"
    assert "gemini" not in result.model_name.lower()
    assert result.category == IncidentCategory.FIRE_ENVIRONMENTAL
    assert result.subcategory == "Smoke Hazard"
    assert result.severity == IncidentSeverity.HIGH
    assert result.language == LanguageDetection.ENGLISH
    assert result.original_description == "Smoke coming from vacant plot"
    assert 0.0 <= result.confidence <= 1.0


def test_504_deadline_exceeded_triggers_fallback():
    """504 Deadline Exceeded triggers deterministic fallback."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("504 Gateway Timeout: Deadline Exceeded")
    classifier = IncidentClassifier(client=mock_client)

    result = classifier.classify_incident("Open manhole on Main Street near the bus stop. Immediate danger of someone falling in.")

    assert result.is_fallback is True
    assert result.source == "local_fallback"
    assert result.model_name == "rule-based-fallback"
    assert result.category == IncidentCategory.INFRASTRUCTURE
    assert result.subcategory == "Open Manhole"
    assert result.severity == IncidentSeverity.CRITICAL


def test_503_unavailable_triggers_fallback():
    """503 Service Unavailable triggers deterministic fallback."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("503 Service Unavailable: Backed off")
    classifier = IncidentClassifier(client=mock_client)

    result = classifier.classify_incident("Suspicious activity reported near bank ATM")

    assert result.is_fallback is True
    assert result.source == "local_fallback"
    assert result.category == IncidentCategory.PUBLIC_SAFETY
    assert result.subcategory == "Suspicious Activity"


def test_fallback_hindi_language_and_classification():
    """Fallback accurately classifies Hindi (Devanagari) reports."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("Deadline exceeded")
    classifier = IncidentClassifier(client=mock_client)

    hindi_input = "मुख्य सड़क पर गहरा गड्ढा है, पानी भरने की वजह से कई बाइक फिसल कर गिर चुकी हैं।"
    result = classifier.classify_incident(hindi_input)

    assert result.is_fallback is True
    assert result.language == LanguageDetection.HINDI
    assert result.category == IncidentCategory.TRAFFIC_ROAD_HAZARD
    assert result.subcategory == "Dangerous Pothole"
    assert result.severity == IncidentSeverity.HIGH
    assert result.original_description == hindi_input


def test_fallback_hinglish_language_and_classification():
    """Fallback accurately classifies Hinglish (Romanized Hindi) reports."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("Deadline exceeded")
    classifier = IncidentClassifier(client=mock_client)

    hinglish_input = "Gali no 4 me pichhle 5 din se street light kharab hai, raat ko bohot andhera rehta hai aur safe nahi lagta."
    result = classifier.classify_incident(hinglish_input)

    assert result.is_fallback is True
    assert result.language == LanguageDetection.HINGLISH
    assert result.category == IncidentCategory.INFRASTRUCTURE
    assert result.subcategory == "Broken Streetlight"
    assert result.severity == IncidentSeverity.MEDIUM
    assert result.original_description == hinglish_input


def test_fallback_preserves_original_description_verbatim():
    """Fallback preserves whitespace, special characters and formatting verbatim."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("Deadline exceeded")
    classifier = IncidentClassifier(client=mock_client)

    raw_text = "  \n URGENT!! Pipe burst @ Sector 14! Street is completely flooded!! \t "
    result = classifier.classify_incident(raw_text)

    assert result.original_description == raw_text
    assert result.is_fallback is True


def test_gemini_success_metadata():
    """Successful Gemini inference identifies Gemini as source and not fallback."""
    mock_payload = {
        "category": "Noise & Public Nuisance",
        "subcategory": "Late Night Music",
        "severity": "Low",
        "language": "English",
        "confidence": 0.88,
        "explanation": "Late night residential noise violation."
    }
    client = create_mock_client(json.dumps(mock_payload))
    classifier = IncidentClassifier(client=client)

    result = classifier.classify_incident("Loud music playing at 2 AM")

    assert result.is_fallback is False
    assert result.source == "gemini"
    assert result.model_name == classifier.config.model_name
    assert "gemini" in result.model_name.lower()
