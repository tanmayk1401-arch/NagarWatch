"""Unit tests for NagarWatch Admin Intelligence Assistant.

Verifies:
1. Incident statistical summaries (totals, resolution rates, queues).
2. Category distributions computed strictly in Python.
3. Priority statistics (Critical/High counts and percentages).
4. Pending vs In Progress vs Resolved operational workflow tracking.
5. Missing and empty dataset handling (prevention of hallucinated metrics).
6. Multilingual support (English, Hindi, Hinglish).
7. Fallback on Gemini timeouts (TimeoutError, 504 Deadline Exceeded) and API failures.
8. Malformed model response handling.
9. Ethical boundary enforcement (decline predictive crime forecasting and neighborhood stigmatization).
"""

import json
from unittest.mock import MagicMock
import pytest

from ai_services.admin_assistant import (
    AdminAssistant,
    AdminAssistantResponse,
    ask_admin_assistant,
    compute_factual_statistics,
)
from ai_services.exceptions import (
    ClassificationValidationError,
    GeminiAPIError,
    GeminiTimeoutError,
)

# Reference sample mock data for tests
SAMPLE_INCIDENTS = [
    {"id": 1, "category": "Infrastructure", "status": "In Progress", "priority_band": "Critical"},
    {"id": 2, "category": "Infrastructure", "status": "Resolved", "priority_band": "High"},
    {"id": 3, "category": "Infrastructure", "status": "Pending Triage", "priority_band": "Moderate"},
    {"id": 4, "category": "Sanitation & Health", "status": "Resolved", "priority_band": "Low"},
    {"id": 5, "category": "Sanitation & Health", "status": "Pending Triage", "priority_band": "Moderate"},
    {"id": 6, "category": "Traffic & Road Hazard", "status": "In Progress", "priority_band": "Critical"},
    {"id": 7, "category": "Traffic & Road Hazard", "status": "Resolved", "priority_band": "High"},
    {"id": 8, "category": "Public Safety", "status": "In Progress", "priority_band": "High"},
    {"id": 9, "category": "Noise & Public Nuisance", "status": "Resolved", "priority_band": "Low"},
    {"id": 10, "category": "Infrastructure", "status": "Resolved", "priority_band": "Moderate"},
]


def create_mock_admin_client(response_text: str):
    """Helper creating a mocked Gen AI client returning the specified text."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


# ==============================================================================
# Factual Statistics Computation Tests (Python Engine)
# ==============================================================================

def test_compute_factual_statistics_from_records():
    """Verify factual numbers are calculated accurately in Python, not Gemini."""
    stats = compute_factual_statistics(SAMPLE_INCIDENTS)

    assert stats["total_incidents"] == 10
    assert stats["category_counts"]["Infrastructure"] == 4
    assert stats["category_counts"]["Sanitation & Health"] == 2
    assert stats["category_counts"]["Traffic & Road Hazard"] == 2
    assert stats["category_percentages"]["Infrastructure"] == 40.0
    assert stats["priority_counts"]["Critical"] == 2
    assert stats["priority_counts"]["High"] == 3
    assert stats["critical_and_high_count"] == 5
    assert stats["critical_and_high_percentage"] == 50.0
    assert stats["status_counts"]["Resolved"] == 5
    assert stats["resolution_rate_percent"] == 50.0
    assert stats["is_empty"] is False


def test_compute_factual_statistics_from_preaggregated_dict():
    """Verify computing stats from a pre-aggregated dictionary."""
    pre_agg = {
        "total_incidents": 50,
        "category_breakdown": {"Infrastructure": 25, "Sanitation & Health": 25},
        "status_breakdown": {"Resolved": 30, "In Progress": 15, "Pending": 5},
        "priority_breakdown": {"Critical": 10, "High": 15, "Moderate": 15, "Low": 10},
    }
    stats = compute_factual_statistics(pre_agg)

    assert stats["total_incidents"] == 50
    assert stats["category_percentages"]["Infrastructure"] == 50.0
    assert stats["resolution_rate_percent"] == 60.0
    assert stats["critical_and_high_count"] == 25
    assert stats["critical_and_high_percentage"] == 50.0


def test_compute_factual_statistics_empty_data():
    """Empty or None input yields 0 counts with is_empty=True."""
    stats_none = compute_factual_statistics(None)
    assert stats_none["total_incidents"] == 0
    assert stats_none["is_empty"] is True

    stats_empty = compute_factual_statistics([])
    assert stats_empty["total_incidents"] == 0
    assert stats_empty["is_empty"] is True


# ==============================================================================
# Analytical Response & Structured Output Tests
# ==============================================================================

def test_incident_summary_analysis():
    """Verify executive summary generation using Gemini."""
    mock_payload = {
        "summary": "10 incidents recorded; Infrastructure is the leading category (40%) with a 50% resolution rate.",
        "key_insights": [
            "50% of reports are Critical or High priority.",
            "Infrastructure comprises 4 of 10 reports.",
            "5 incidents are currently resolved."
        ],
        "answer": "Executive Summary: 10 incidents were analyzed with 5 resolved, 3 in progress, and 2 pending triage.",
        "limitations": ["Sample size of 10 reports."]
    }
    client = create_mock_admin_client(json.dumps(mock_payload))
    assistant = AdminAssistant(client=client)

    result = assistant.ask("Summarize our current incident status and trends.", data=SAMPLE_INCIDENTS)

    assert isinstance(result, AdminAssistantResponse)
    assert result.source == "gemini"
    assert "10 incidents" in result.summary
    assert len(result.key_insights) == 3
    assert result.statistics_used["total_incidents"] == 10
    assert result.statistics_used["critical_and_high_count"] == 5


def test_category_distribution_analysis():
    """Verify category distribution analysis."""
    mock_payload = {
        "summary": "Infrastructure represents 40% of all reported issues.",
        "key_insights": ["Infrastructure: 40%", "Sanitation: 20%", "Traffic: 20%"],
        "answer": "The category breakdown shows Infrastructure as the predominant civic concern.",
        "limitations": []
    }
    client = create_mock_admin_client(json.dumps(mock_payload))
    assistant = AdminAssistant(client=client)

    result = assistant.ask("What is the distribution of incident categories?", data=SAMPLE_INCIDENTS)
    assert "Infrastructure" in result.summary
    assert result.statistics_used["category_counts"]["Infrastructure"] == 4


def test_priority_statistics_analysis():
    """Verify high-priority and critical incident trend analysis."""
    mock_payload = {
        "summary": "5 incidents (50%) are categorized as Critical or High priority.",
        "key_insights": ["2 Critical incidents require immediate dispatch.", "3 High priority incidents."],
        "answer": "Urgent incidents account for half of current municipal backlog.",
        "limitations": []
    }
    client = create_mock_admin_client(json.dumps(mock_payload))
    assistant = AdminAssistant(client=client)

    result = assistant.ask("How many critical and high priority incidents do we have?", data=SAMPLE_INCIDENTS)
    assert result.statistics_used["critical_and_high_count"] == 5
    assert result.statistics_used["priority_counts"]["Critical"] == 2


def test_pending_and_resolved_reports_analysis():
    """Verify workflow queue tracking (pending, in-progress, resolved)."""
    mock_payload = {
        "summary": "5 reports are resolved, 3 are in progress, and 2 are pending triage.",
        "key_insights": ["Resolution rate is 50.0%.", "5 active reports remain in the queue."],
        "answer": "50% of reports are resolved, with 5 active issues undergoing triage or repair.",
        "limitations": []
    }
    client = create_mock_admin_client(json.dumps(mock_payload))
    assistant = AdminAssistant(client=client)

    result = assistant.ask("What is our resolution rate and active queue?", data=SAMPLE_INCIDENTS)
    assert result.statistics_used["resolution_rate_percent"] == 50.0
    assert result.statistics_used["status_counts"]["Resolved"] == 5


# ==============================================================================
# Missing Data & Anti-Hallucination Tests
# ==============================================================================

def test_missing_data_prevention_of_invented_statistics():
    """When data is missing or empty, assistant clearly states so without inventing stats."""
    assistant = AdminAssistant(client=MagicMock(), fallback_enabled=True)

    result = assistant.ask("What are our incident trends?", data=None)

    assert result.statistics_used["is_empty"] is True
    assert result.statistics_used["total_incidents"] == 0
    assert "no incident" in result.summary.lower() or "empty" in result.summary.lower()
    assert len(result.limitations) > 0


# ==============================================================================
# Multilingual Administrative Queries (Hindi, Hinglish, English)
# ==============================================================================

def test_hindi_administrative_query_fallback():
    """Verify Hindi administrative briefing."""
    assistant = AdminAssistant(client=MagicMock(), fallback_enabled=True)
    hindi_query = "सभी घटनाओं का सांख्यिकीय सारांश और प्राथमिकताओं की स्थिति बताएं।"

    result = assistant.ask(hindi_query, data=SAMPLE_INCIDENTS)

    assert result.source == "local_fallback"
    assert "कुल 10 घटनाएं" in result.summary
    assert "Infrastructure" in result.summary
    assert result.statistics_used["total_incidents"] == 10


def test_hinglish_administrative_query_fallback():
    """Verify Hinglish administrative briefing."""
    assistant = AdminAssistant(client=MagicMock(), fallback_enabled=True)
    hinglish_query = "Total incidents ka status aur category breakdown batao."

    result = assistant.ask(hinglish_query, data=SAMPLE_INCIDENTS)

    assert result.source == "local_fallback"
    assert "Total 10 incidents" in result.summary
    assert "Infrastructure" in result.summary
    assert result.statistics_used["total_incidents"] == 10


# ==============================================================================
# Ethical Boundaries: Unsupported Analytical Requests
# ==============================================================================

def test_unsupported_predictive_crime_query_declined():
    """Assistant must decline requests to predict crimes or stigmatize neighborhoods."""
    assistant = AdminAssistant(client=MagicMock())

    result = assistant.ask("Can you predict which neighborhood will have the most crime next month?", data=SAMPLE_INCIDENTS)

    assert result.source == "local_fallback"
    assert "prohibited" in result.summary.lower() or "declined" in result.summary.lower()
    assert "predictive crime" in result.answer.lower()
    assert "prohibited" in result.limitations[0].lower() or "declined" in result.limitations[0].lower()


def test_unsupported_dangerous_neighborhood_query_declined():
    """Assistant must decline naming the 'most dangerous neighborhood'."""
    result = ask_admin_assistant("Which area is the most dangerous neighborhood in our city?", data=SAMPLE_INCIDENTS)

    assert result.source == "local_fallback"
    assert "unsupported" in result.answer.lower() or "predictive" in result.answer.lower()


# ==============================================================================
# Timeout, API Errors & Fallback Tests
# ==============================================================================

def test_gemini_timeout_triggers_deterministic_fallback():
    """TimeoutError triggers local deterministic briefing without leaking errors."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("Deadline exceeded after 30000ms")
    assistant = AdminAssistant(client=mock_client, fallback_enabled=True)

    result = assistant.ask("Summarize incidents", data=SAMPLE_INCIDENTS)

    assert result.source == "local_fallback"
    assert "10 recorded incidents" in result.summary
    assert result.statistics_used["total_incidents"] == 10


def test_gemini_timeout_raises_when_fallback_disabled():
    """TimeoutError raises GeminiTimeoutError when fallback is disabled."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("Deadline exceeded after 30000ms")
    assistant = AdminAssistant(client=mock_client, fallback_enabled=False)

    with pytest.raises(GeminiTimeoutError, match="timed out"):
        assistant.ask("Summarize incidents", data=SAMPLE_INCIDENTS)


def test_upstream_api_failure_raises_when_fallback_disabled():
    """Upstream API failures raise GeminiAPIError when fallback is disabled."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("500 Internal Server Error")
    assistant = AdminAssistant(client=mock_client, fallback_enabled=False)

    with pytest.raises(GeminiAPIError, match="Google Gemini API error"):
        assistant.ask("Summarize incidents", data=SAMPLE_INCIDENTS)


def test_malformed_response_triggers_fallback_or_validation_error():
    """Malformed model outputs trigger fallback when enabled, or raise validation error when disabled."""
    client = create_mock_admin_client("NOT VALID JSON")

    # With fallback enabled (default)
    assistant_with_fallback = AdminAssistant(client=client, fallback_enabled=True)
    fallback_res = assistant_with_fallback.ask("Summarize incidents", data=SAMPLE_INCIDENTS)
    assert fallback_res.source == "local_fallback"
    assert "10" in fallback_res.summary

    # With fallback disabled
    assistant_no_fallback = AdminAssistant(client=client, fallback_enabled=False)
    with pytest.raises(ClassificationValidationError, match="schema validation"):
        assistant_no_fallback.ask("Summarize incidents", data=SAMPLE_INCIDENTS)


def test_empty_query_raises_value_error():
    """Empty query string must raise ValueError."""
    assistant = AdminAssistant(client=MagicMock())
    with pytest.raises(ValueError, match="non-empty string"):
        assistant.ask("")


def test_to_dict_serialization():
    """Verify dictionary serialization for AdminAssistantResponse."""
    mock_payload = {
        "summary": "Brief summary.",
        "key_insights": ["Insight 1"],
        "answer": "Detailed answer.",
        "limitations": ["Sample limitation"]
    }
    client = create_mock_admin_client(json.dumps(mock_payload))
    result = ask_admin_assistant("Test question", data=SAMPLE_INCIDENTS, client=client)
    data = result.to_dict()

    assert isinstance(data, dict)
    assert data["summary"] == "Brief summary."
    assert data["answer"] == "Detailed answer."
    assert data["source"] == "gemini"
    assert "statistics_used" in data
    assert "evaluated_at" in data
