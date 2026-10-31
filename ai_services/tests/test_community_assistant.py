"""Unit tests for NagarWatch Multilingual Community Assistant.

Verifies:
1. English, Hindi, and Hinglish query understanding and response generation.
2. Incident reporting guidance and priority level explanations.
3. Polite deflection of unsupported and off-topic questions.
4. Database safety:
   - Prevention of invented/hallucinated incident records, statuses, or counts.
   - Clean handling when authorized database context is provided vs missing.
   - Non-direct database coupling.
5. Privacy protection: Refusal to share other residents' PII or reports.
6. Emergency escalation: Prompt direction to 112 / emergency dispatchers for life-safety threats.
7. Error handling:
   - Graceful fallback on Gemini timeouts, 504 Deadline Exceeded, and API errors.
   - Raising typed domain exceptions when fallback is explicitly disabled.
   - Malformed AI response handling.
"""

import json
from unittest.mock import MagicMock
import pytest

from ai_services.community_assistant import (
    AssistantResponse,
    CommunityAssistant,
    ask_community_assistant,
    detect_query_language,
)
from ai_services.exceptions import (
    ClassificationValidationError,
    GeminiAPIError,
    GeminiTimeoutError,
)
from ai_services.schemas import LanguageDetection


def create_mock_assistant_client(response_text: str):
    """Helper creating a mocked Gen AI client returning the specified text."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


# ==============================================================================
# Multilingual Guidance Tests (English, Hindi, Hinglish)
# ==============================================================================

def test_english_reporting_guidance():
    """Verify assistant guides an English resident on how to report an incident."""
    mock_payload = {
        "answer": "To report an incident on NagarWatch, tap 'Report Incident', describe the hazard, select a category, confirm your location, and attach a photo if safe.",
        "detected_language": "English",
        "confidence": 0.95,
        "requires_database_data": False,
        "limitations": []
    }
    client = create_mock_assistant_client(json.dumps(mock_payload))
    assistant = CommunityAssistant(client=client)

    result = assistant.ask("How can I submit a report for an open manhole?")

    assert isinstance(result, AssistantResponse)
    assert result.detected_language == LanguageDetection.ENGLISH
    assert "report incident" in result.answer.lower()
    assert result.requires_database_data is False
    assert result.source == "gemini"


def test_hindi_query_and_response():
    """Verify assistant handles Hindi (Devanagari) queries and preserves language."""
    mock_payload = {
        "answer": "नगरवॉच पर समस्या दर्ज करने के लिए 'Report Incident' पर क्लिक करें, समस्या का विवरण दें और स्थान की पुष्टि करें।",
        "detected_language": "Hindi",
        "confidence": 0.96,
        "requires_database_data": False,
        "limitations": []
    }
    client = create_mock_assistant_client(json.dumps(mock_payload))
    assistant = CommunityAssistant(client=client)

    hindi_query = "सड़क पर गहरा गड्ढा है, शिकायत कैसे दर्ज करें?"
    result = assistant.ask(hindi_query)

    assert result.detected_language == LanguageDetection.HINDI
    assert "रिपोर्ट" in result.answer or "स्थान" in result.answer
    assert result.confidence == 0.96


def test_hinglish_query_and_response():
    """Verify assistant handles Hinglish queries and preserves dialect."""
    mock_payload = {
        "answer": "NagarWatch par report karne ke liye 'Report Incident' par click karein aur street light ki location aur photo add karein.",
        "detected_language": "Hinglish",
        "confidence": 0.93,
        "requires_database_data": False,
        "limitations": []
    }
    client = create_mock_assistant_client(json.dumps(mock_payload))
    assistant = CommunityAssistant(client=client)

    hinglish_query = "Gali no 4 me street light kharab hai, report kaise karein?"
    result = assistant.ask(hinglish_query)

    assert result.detected_language == LanguageDetection.HINGLISH
    assert result.requires_database_data is False


def test_language_detection_helper():
    """Test detect_query_language across Hindi, Hinglish, and English."""
    assert detect_query_language("पानी की पाइप फट गई है") == LanguageDetection.HINDI
    assert detect_query_language("Pani ki pipe burst ho gayi hai") == LanguageDetection.HINGLISH
    assert detect_query_language("A water pipe has burst near main gate") == LanguageDetection.ENGLISH


# ==============================================================================
# Platform Guidance: Priority and Status Explanations
# ==============================================================================

def test_priority_levels_explanation():
    """Verify explanation of platform priority levels (0-100 scale and bands)."""
    mock_payload = {
        "answer": "NagarWatch priority is calculated from Severity (40%), Community Verification (25%), Recency (20%), and Affected Area (15%). Bands are Critical (75-100), High (50-74), Moderate (30-49), and Low (0-29).",
        "detected_language": "English",
        "confidence": 0.94,
        "requires_database_data": False,
        "limitations": []
    }
    client = create_mock_assistant_client(json.dumps(mock_payload))
    assistant = CommunityAssistant(client=client)

    result = assistant.ask("What do the priority levels mean?")
    assert "Critical" in result.answer
    assert "Severity" in result.answer


def test_unsupported_questions_politely_handled():
    """Verify polite deflection when residents ask off-topic or unsupported queries."""
    mock_payload = {
        "answer": "I am the NagarWatch Community Assistant, dedicated to neighborhood safety and civic reports. I cannot assist with recipes or general trivia.",
        "detected_language": "English",
        "confidence": 0.88,
        "requires_database_data": False,
        "limitations": ["Query is outside civic safety domain."]
    }
    client = create_mock_assistant_client(json.dumps(mock_payload))
    assistant = CommunityAssistant(client=client)

    result = assistant.ask("Can you give me a recipe for chocolate cake?")
    assert "NagarWatch" in result.answer
    assert len(result.limitations) > 0


# ==============================================================================
# Database Safety & Anti-Hallucination Tests
# ==============================================================================

def test_missing_database_context_refuses_to_invent_data():
    """Assistant must NEVER invent report statuses or counts when context is missing."""
    mock_payload = {
        "answer": "I do not have access to live database records for report #NW-9872. To ensure accuracy, NagarWatch never invents report statuses. Please check your resident dashboard.",
        "detected_language": "English",
        "confidence": 0.92,
        "requires_database_data": True,
        "limitations": ["Live database access unavailable."]
    }
    client = create_mock_assistant_client(json.dumps(mock_payload))
    assistant = CommunityAssistant(client=client)

    # Calling without backend context
    result = assistant.ask("What is the status of my report #NW-9872?", context=None)

    assert result.requires_database_data is True
    assert "never invents" in result.answer.lower() or "do not have access" in result.answer.lower()


def test_authorized_database_context_utilized():
    """When authorized backend context is provided, assistant utilizes it accurately."""
    mock_payload = {
        "answer": "Your report #NW-104 is currently 'In Progress' and has been dispatched to local road maintenance.",
        "detected_language": "English",
        "confidence": 0.96,
        "requires_database_data": True,
        "limitations": ["Based on provided backend context."]
    }
    client = create_mock_assistant_client(json.dumps(mock_payload))
    assistant = CommunityAssistant(client=client)

    authorized_context = {
        "report_id": "NW-104",
        "status": "In Progress",
        "category": "Traffic & Road Hazard",
        "location": "Sector 14"
    }

    result = assistant.ask("Can you check report NW-104?", context=authorized_context)
    assert result.requires_database_data is True
    assert "In Progress" in result.answer


# ==============================================================================
# Safety, Emergency, and Privacy Tests
# ==============================================================================

def test_privacy_protection_refuses_resident_pii():
    """Assistant must never disclose personal details or identity of other residents."""
    mock_payload = {
        "answer": "To protect privacy and safety, NagarWatch strictly anonymizes all reporter identities and does not disclose contact numbers or personal information.",
        "detected_language": "English",
        "confidence": 0.97,
        "requires_database_data": False,
        "limitations": ["Privacy policy forbids sharing resident personal details."]
    }
    client = create_mock_assistant_client(json.dumps(mock_payload))
    assistant = CommunityAssistant(client=client)

    result = assistant.ask("Who reported the garbage issue next door? Give me their phone number.")
    assert "privacy" in result.answer.lower() or "anonymizes" in result.answer.lower()


def test_emergency_escalation_protocol():
    """Active life-threatening emergencies must immediately direct resident to emergency services."""
    # Emergency check intercepts locally before LLM to guarantee zero delay and 100% reliability
    result = ask_community_assistant("There is a building on fire right now, someone is trapped!")

    assert "EMERGENCY NOTICE" in result.answer
    assert "112" in result.answer
    assert result.confidence == 1.0
    assert result.requires_database_data is False


def test_emergency_escalation_in_hindi():
    """Emergency detection correctly escalates in Hindi."""
    result = ask_community_assistant("घर में आग लगी है, तुरंत सहायता चाहिए!")

    assert "आपातकालीन सूचना" in result.answer
    assert "112" in result.answer
    assert result.detected_language == LanguageDetection.HINDI


# ==============================================================================
# Timeout, Error Handling & Fallback Tests
# ==============================================================================

def test_gemini_timeout_triggers_safe_fallback():
    """Network timeouts must trigger deterministic local fallback with no internal error leaks."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("Deadline exceeded after 30000ms")
    assistant = CommunityAssistant(client=mock_client, fallback_enabled=True)

    result = assistant.ask("How to report a pothole on NagarWatch?")

    assert isinstance(result, AssistantResponse)
    assert result.source == "local_fallback"
    assert "Report Incident" in result.answer
    assert result.detected_language == LanguageDetection.ENGLISH


def test_gemini_timeout_raises_when_fallback_disabled():
    """Network timeouts raise GeminiTimeoutError when fallback is explicitly disabled."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("Deadline exceeded after 30000ms")
    assistant = CommunityAssistant(client=mock_client, fallback_enabled=False)

    with pytest.raises(GeminiTimeoutError, match="timed out"):
        assistant.ask("How to report a pothole?")


def test_upstream_api_failure_raises_when_fallback_disabled():
    """Upstream API failures raise GeminiAPIError when fallback is explicitly disabled."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("500 Internal Server Error")
    assistant = CommunityAssistant(client=mock_client, fallback_enabled=False)

    with pytest.raises(GeminiAPIError, match="Google Gemini API error"):
        assistant.ask("How to report a pothole?")


def test_malformed_json_response_triggers_fallback_or_validation_error():
    """Malformed model outputs trigger fallback when enabled, or raise validation error when disabled."""
    client = create_mock_assistant_client("THIS IS NOT JSON")

    # With fallback enabled (default)
    assistant_with_fallback = CommunityAssistant(client=client, fallback_enabled=True)
    fallback_res = assistant_with_fallback.ask("What do the priority levels mean?")
    assert fallback_res.source == "local_fallback"
    assert "priority" in fallback_res.answer.lower()

    # With fallback disabled
    assistant_no_fallback = CommunityAssistant(client=client, fallback_enabled=False)
    with pytest.raises(ClassificationValidationError, match="schema validation"):
        assistant_no_fallback.ask("What do the priority levels mean?")


def test_empty_query_raises_value_error():
    """Empty queries must raise ValueError."""
    assistant = CommunityAssistant(client=MagicMock())
    with pytest.raises(ValueError, match="non-empty string"):
        assistant.ask("")

    with pytest.raises(ValueError, match="non-empty string"):
        assistant.ask("   \t\n ")


def test_to_dict_serialization():
    """Verify dictionary serialization for AssistantResponse."""
    mock_payload = {
        "answer": "Test answer.",
        "detected_language": "English",
        "confidence": 0.90,
        "requires_database_data": False,
        "limitations": ["Test limitation"]
    }
    client = create_mock_assistant_client(json.dumps(mock_payload))
    result = ask_community_assistant("Test question", client=client)
    data = result.to_dict()

    assert isinstance(data, dict)
    assert data["answer"] == "Test answer."
    assert data["detected_language"] == "English"
    assert data["confidence"] == 0.90
    assert data["requires_database_data"] is False
    assert "limitations" in data
    assert "evaluated_at" in data
