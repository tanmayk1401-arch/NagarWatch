"""Unit tests for NagarWatch Duplicate Incident Detection Service.

Verifies:
1. Exact weighted formula calculation: D = 0.40G + 0.25C + 0.15T + 0.20S.
2. All three decision thresholds:
   - Below 60: Separate incidents.
   - 60–79.99: Possible duplicate — human review required.
   - 80–100: Strong duplicate candidate — human review required.
3. Identical reports (100% match) and completely unrelated reports (0% match).
4. Safe handling of missing coordinates (G falls back to 0.0 safely).
5. Safe handling of missing or incomplete incident information.
6. Safe handling of invalid inputs (rejection on calculate_from_components, safe fallback on report fields).
7. Human-in-the-loop review policy (no auto-merging or deleting).
"""

from datetime import datetime, timezone
import pytest

from ai_services.duplicate_service import (
    DuplicateAssessment,
    DuplicateDecision,
    DuplicateService,
    calculate_category_similarity,
    calculate_geographic_similarity,
    calculate_text_similarity,
    calculate_time_similarity,
    detect_duplicates,
    determine_duplicate_decision,
    haversine_distance_meters,
)


# ==============================================================================
# Formula Accuracy Tests
# ==============================================================================

def test_weighted_score_exact_calculation():
    """Verify D = 0.40G + 0.25C + 0.15T + 0.20S calculation."""
    # G=100, C=80, T=60, S=50
    # D = (0.40 * 100) + (0.25 * 80) + (0.15 * 60) + (0.20 * 50)
    # D = 40.0 + 20.0 + 9.0 + 10.0 = 79.0
    assessment = DuplicateService.calculate_from_components(
        geographic_similarity=100.0,
        category_similarity=80.0,
        time_similarity=60.0,
        text_similarity=50.0,
    )

    assert assessment.score == 79.0
    assert assessment.geographic_similarity == 100.0
    assert assessment.category_similarity == 80.0
    assert assessment.time_similarity == 60.0
    assert assessment.text_similarity == 50.0
    assert assessment.g == 100.0
    assert assessment.c == 80.0
    assert assessment.t == 60.0
    assert assessment.s == 50.0
    assert assessment.decision == DuplicateDecision.POSSIBLE_DUPLICATE
    assert assessment.requires_human_review is True


def test_zero_and_maximum_bounds():
    """Verify formula at boundary extremes (0.0 and 100.0)."""
    min_res = DuplicateService.calculate_from_components(0.0, 0.0, 0.0, 0.0)
    assert min_res.score == 0.0
    assert min_res.decision == DuplicateDecision.SEPARATE
    assert min_res.requires_human_review is False

    max_res = DuplicateService.calculate_from_components(100.0, 100.0, 100.0, 100.0)
    assert max_res.score == 100.0
    assert max_res.decision == DuplicateDecision.STRONG_DUPLICATE
    assert max_res.requires_human_review is True


# ==============================================================================
# Decision Threshold Tests
# ==============================================================================

@pytest.mark.parametrize(
    "score,expected_decision,expected_review",
    [
        (0.0, DuplicateDecision.SEPARATE, False),
        (35.5, DuplicateDecision.SEPARATE, False),
        (59.99, DuplicateDecision.SEPARATE, False),
        (60.0, DuplicateDecision.POSSIBLE_DUPLICATE, True),
        (70.0, DuplicateDecision.POSSIBLE_DUPLICATE, True),
        (79.99, DuplicateDecision.POSSIBLE_DUPLICATE, True),
        (80.0, DuplicateDecision.STRONG_DUPLICATE, True),
        (92.5, DuplicateDecision.STRONG_DUPLICATE, True),
        (100.0, DuplicateDecision.STRONG_DUPLICATE, True),
    ],
)
def test_duplicate_decision_thresholds(score, expected_decision, expected_review):
    """Verify exact boundaries for all three decision thresholds."""
    decision = determine_duplicate_decision(score)
    assert decision == expected_decision
    assert (decision != DuplicateDecision.SEPARATE) == expected_review


# ==============================================================================
# Identical and Unrelated Reports Tests
# ==============================================================================

def test_identical_reports():
    """Identical incidents yield 100.0 score and STRONG_DUPLICATE decision."""
    now_iso = "2026-10-30T10:00:00Z"
    incident_a = {
        "description": "Deep dangerous pothole on Main Street near bus stop causing bike skids",
        "category": "Traffic & Road Hazard",
        "timestamp": now_iso,
        "latitude": 28.6139,
        "longitude": 77.2090,
    }
    incident_b = {
        "description": "Deep dangerous pothole on Main Street near bus stop causing bike skids",
        "category": "Traffic & Road Hazard",
        "timestamp": now_iso,
        "latitude": 28.6139,
        "longitude": 77.2090,
    }

    assessment = detect_duplicates(incident_a, incident_b)

    assert assessment.score == 100.0
    assert assessment.geographic_similarity == 100.0
    assert assessment.category_similarity == 100.0
    assert assessment.time_similarity == 100.0
    assert assessment.text_similarity == 100.0
    assert assessment.decision == DuplicateDecision.STRONG_DUPLICATE
    assert assessment.requires_human_review is True
    assert "human dispatcher review is required" in assessment.explanation


def test_unrelated_reports():
    """Completely unrelated incidents yield low score and SEPARATE decision."""
    incident_a = {
        "description": "Open manhole on Sector 14 market lane",
        "category": "Infrastructure",
        "timestamp": "2026-10-01T08:00:00Z",
        "latitude": 28.6139,
        "longitude": 77.2090,
    }
    # Different location (~20 km away), category, text, time (weeks apart)
    incident_b = {
        "description": "Loud music blaring at late night party",
        "category": "Noise & Public Nuisance",
        "timestamp": "2026-10-25T23:30:00Z",
        "latitude": 28.4595,
        "longitude": 77.0266,
    }

    assessment = detect_duplicates(incident_a, incident_b)

    assert assessment.score < 60.0
    assert assessment.decision == DuplicateDecision.SEPARATE
    assert assessment.requires_human_review is False


# ==============================================================================
# Missing Information Handling Tests
# ==============================================================================

def test_missing_coordinates_handled_safely():
    """Missing coordinates safely fall back to G=0.0 without crashing."""
    now_iso = "2026-10-30T10:00:00Z"
    incident_a = {
        "description": "Water pipe burst flooding street completely",
        "category": "Infrastructure",
        "timestamp": now_iso,
        "latitude": None,
        "longitude": None,
    }
    incident_b = {
        "description": "Water pipe burst flooding street completely",
        "category": "Infrastructure",
        "timestamp": now_iso,
        "latitude": 28.6139,
        "longitude": 77.2090,
    }

    assessment = detect_duplicates(incident_a, incident_b)

    # G is 0.0 because incident_a lacks coordinates
    assert assessment.geographic_similarity == 0.0
    assert assessment.category_similarity == 100.0
    assert assessment.time_similarity == 100.0
    assert assessment.text_similarity == 100.0

    # D = 0.40(0) + 0.25(100) + 0.15(100) + 0.20(100) = 0 + 25 + 15 + 20 = 60.0
    assert assessment.score == 60.0
    assert assessment.decision == DuplicateDecision.POSSIBLE_DUPLICATE
    assert assessment.requires_human_review is True
    assert "missing coordinates" in assessment.explanation


def test_missing_or_incomplete_incident_information():
    """Handles missing description, category, and timestamps safely."""
    incident_a = {}
    incident_b = {}

    assessment = detect_duplicates(incident_a, incident_b)

    assert assessment.score == 0.0
    assert assessment.geographic_similarity == 0.0
    assert assessment.category_similarity == 0.0
    assert assessment.time_similarity == 0.0
    assert assessment.text_similarity == 0.0
    assert assessment.decision == DuplicateDecision.SEPARATE
    assert assessment.requires_human_review is False
    assert "Incomplete signals" in assessment.explanation


def test_partial_text_and_haversine_distance():
    """Verify geographic and text similarity calculations across partial matches."""
    # Points roughly 200m apart in Delhi
    coord1 = (28.61390, 77.20900)
    coord2 = (28.61500, 77.20900)

    dist = haversine_distance_meters(coord1, coord2)
    assert 100.0 < dist < 150.0  # Approx 122m

    # Within 1000m radius, similarity should be around (1 - 122/1000) * 100 ≈ 87.8
    geo_sim = calculate_geographic_similarity(coord1, coord2, max_radius_meters=1000.0)
    assert 85.0 <= geo_sim <= 90.0

    # Text similarity with minor phrasing difference
    text1 = "Garbage piled up on corner of 5th cross road"
    text2 = "Garbage piled up on corner of 5th cross street"
    sim = calculate_text_similarity(text1, text2)
    assert sim > 85.0


# ==============================================================================
# Safe Handling of Invalid Inputs
# ==============================================================================

@pytest.mark.parametrize(
    "invalid_val",
    [-0.5, 100.5, -20.0, 150.0],
)
def test_calculate_from_components_rejects_out_of_bounds(invalid_val):
    """Direct component calculator rejects values strictly outside [0, 100]."""
    with pytest.raises(ValueError, match="must be between 0.0 and 100.0"):
        DuplicateService.calculate_from_components(invalid_val, 50, 50, 50)


@pytest.mark.parametrize(
    "invalid_type",
    ["high", None, True, False, [50]],
)
def test_calculate_from_components_rejects_non_numerical(invalid_type):
    """Direct component calculator rejects non-numerical inputs with TypeError."""
    with pytest.raises(TypeError, match="must be a numerical float or int"):
        DuplicateService.calculate_from_components(50, invalid_type, 50, 50)


def test_calculate_from_components_rejects_nan_inf():
    """Direct component calculator rejects NaN and Infinity."""
    with pytest.raises(ValueError, match="cannot be NaN or Infinite"):
        DuplicateService.calculate_from_components(float("nan"), 50, 50, 50)

    with pytest.raises(ValueError, match="cannot be NaN or Infinite"):
        DuplicateService.calculate_from_components(50, 50, float("inf"), 50)


def test_malformed_report_values_fall_back_safely():
    """Malformed coordinates and unparseable dates in report dicts fall back gracefully."""
    incident_a = {
        "latitude": "not-a-number",
        "longitude": [123],
        "timestamp": "invalid-timestamp-string",
        "category": None,
        "description": None,
    }
    incident_b = {
        "latitude": 999.0,  # Invalid latitude (> 90)
        "longitude": 77.2090,
        "timestamp": 1234567890,
        "category": "Infrastructure",
        "description": "Valid description",
    }

    assessment = detect_duplicates(incident_a, incident_b)
    assert assessment.score == 0.0
    assert assessment.decision == DuplicateDecision.SEPARATE
    assert assessment.requires_human_review is False


# ==============================================================================
# Policy & Serialization Tests
# ==============================================================================

def test_no_automatic_action_policy():
    """Policy requirement: Duplicate detection never mutates or drops reports."""
    now_iso = "2026-10-30T10:00:00Z"
    incident_a = {
        "id": 1,
        "description": "Broken lamp post on 5th avenue",
        "category": "Infrastructure",
        "timestamp": now_iso,
        "latitude": 28.6139,
        "longitude": 77.2090,
    }
    incident_b = {
        "id": 2,
        "description": "Broken lamp post on 5th avenue",
        "category": "Infrastructure",
        "timestamp": now_iso,
        "latitude": 28.6139,
        "longitude": 77.2090,
    }

    # Copy of inputs before comparison
    orig_a = dict(incident_a)
    orig_b = dict(incident_b)

    assessment = detect_duplicates(incident_a, incident_b)

    # Input reports must remain completely untouched
    assert incident_a == orig_a
    assert incident_b == orig_b
    assert assessment.requires_human_review is True
    assert "never automatically merged or deleted" in assessment.explanation


def test_to_dict_serialization():
    """Assessment cleanly converts to dictionary."""
    assessment = DuplicateService.calculate_from_components(85.0, 100.0, 75.0, 80.0)
    data = assessment.to_dict()

    assert isinstance(data, dict)
    assert data["score"] == 86.25
    assert data["decision"] == DuplicateDecision.STRONG_DUPLICATE.value
    assert data["geographic_similarity"] == 85.0
    assert data["category_similarity"] == 100.0
    assert data["time_similarity"] == 75.0
    assert data["text_similarity"] == 80.0
    assert data["requires_human_review"] is True
    assert isinstance(data["explanation"], str)
