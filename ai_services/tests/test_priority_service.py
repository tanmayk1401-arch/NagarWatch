"""Comprehensive unit tests for NagarWatch Priority Intelligence Service.

Tests:
1. Exact formula calculation: Priority = (0.40 * Sev) + (0.25 * Ver) + (0.20 * Rec) + (0.15 * Area).
2. Priority band boundary classifications (0-29: Low, 30-49: Moderate, 50-74: High, 75-100: Critical).
3. Input validation: Rejection of negative numbers, >100, non-numbers, NaN, Inf.
4. Safety escalation: Flagging serious safety incidents for immediate human review regardless of score.
5. Verification independence: Low community votes never suppress serious incidents.
6. Human-readable explanation and dictionary serialization.
"""

import math
import pytest

from ai_services.priority_service import (
    PriorityAssessment,
    PriorityBand,
    PriorityService,
    calculate_priority,
)


# ==============================================================================
# Formula Accuracy Tests
# ==============================================================================

def test_formula_exact_weighted_calculation():
    """Verify exact formula calculation with known reference components."""
    # (0.40 * 80) + (0.25 * 60) + (0.20 * 50) + (0.15 * 40)
    # = 32.0 + 15.0 + 10.0 + 6.0 = 63.00
    assessment = calculate_priority(
        severity=80.0,
        verification=60.0,
        recency=50.0,
        affected_area=40.0,
    )

    assert assessment.score == 63.00
    assert assessment.band == PriorityBand.HIGH
    assert assessment.severity == 80.0
    assert assessment.verification == 60.0
    assert assessment.recency == 50.0
    assert assessment.affected_area == 40.0


def test_zero_and_maximum_boundaries():
    """Verify formula at 0.0 absolute minimum and 100.0 absolute maximum."""
    # Minimum boundary
    min_assessment = calculate_priority(0.0, 0.0, 0.0, 0.0)
    assert min_assessment.score == 0.0
    assert min_assessment.band == PriorityBand.LOW

    # Maximum boundary
    max_assessment = calculate_priority(100.0, 100.0, 100.0, 100.0)
    assert max_assessment.score == 100.0
    assert max_assessment.band == PriorityBand.CRITICAL


# ==============================================================================
# Priority Band Boundary Tests
# ==============================================================================

@pytest.mark.parametrize(
    "score,expected_band",
    [
        (0.0, PriorityBand.LOW),
        (15.5, PriorityBand.LOW),
        (29.0, PriorityBand.LOW),
        (29.99, PriorityBand.LOW),
        (30.0, PriorityBand.MODERATE),
        (40.0, PriorityBand.MODERATE),
        (49.0, PriorityBand.MODERATE),
        (49.99, PriorityBand.MODERATE),
        (50.0, PriorityBand.HIGH),
        (65.0, PriorityBand.HIGH),
        (74.0, PriorityBand.HIGH),
        (74.99, PriorityBand.HIGH),
        (75.0, PriorityBand.CRITICAL),
        (90.0, PriorityBand.CRITICAL),
        (100.0, PriorityBand.CRITICAL),
    ],
)
def test_priority_band_thresholds(score, expected_band):
    """Verify boundary thresholds for Low, Moderate, High, Critical bands."""
    band = PriorityService.determine_band(score)
    assert band == expected_band


# ==============================================================================
# Input Validation & Boundary Protection
# ==============================================================================

@pytest.mark.parametrize(
    "invalid_val",
    [-0.01, -10.0, 100.01, 150.0],
)
def test_reject_out_of_bounds_inputs(invalid_val):
    """Reject values strictly outside 0.0 to 100.0 with ValueError."""
    with pytest.raises(ValueError, match="must be between 0.0 and 100.0"):
        calculate_priority(severity=invalid_val, verification=50, recency=50, affected_area=50)

    with pytest.raises(ValueError, match="must be between 0.0 and 100.0"):
        calculate_priority(severity=50, verification=invalid_val, recency=50, affected_area=50)

    with pytest.raises(ValueError, match="must be between 0.0 and 100.0"):
        calculate_priority(severity=50, verification=50, recency=invalid_val, affected_area=50)

    with pytest.raises(ValueError, match="must be between 0.0 and 100.0"):
        calculate_priority(severity=50, verification=50, recency=50, affected_area=invalid_val)


@pytest.mark.parametrize(
    "non_numerical_val",
    ["high", None, True, False, [50], {"val": 50}],
)
def test_reject_non_numerical_inputs(non_numerical_val):
    """Reject non-float and non-int inputs with TypeError."""
    with pytest.raises(TypeError, match="must be a numerical float or int"):
        calculate_priority(severity=non_numerical_val, verification=50, recency=50, affected_area=50)


def test_reject_nan_and_infinity():
    """Reject NaN and Infinite values."""
    with pytest.raises(ValueError, match="cannot be NaN or Infinite"):
        calculate_priority(float("nan"), 50, 50, 50)

    with pytest.raises(ValueError, match="cannot be NaN or Infinite"):
        calculate_priority(50, float("inf"), 50, 50)


# ==============================================================================
# Safety Escalation & Community Vote Independence Tests
# ==============================================================================

def test_serious_safety_incident_flagged_regardless_of_score():
    """Serious safety incident must be flagged for immediate review even with low score."""
    # Low score inputs that calculate into 'Low' band
    # (0.40 * 40) + (0.25 * 10) + (0.20 * 20) + (0.15 * 10) = 16 + 2.5 + 4 + 1.5 = 24.0
    assessment = calculate_priority(
        severity=40.0,
        verification=10.0,
        recency=20.0,
        affected_area=10.0,
        is_serious_incident=True,
    )

    assert assessment.score == 24.0
    assert assessment.band == PriorityBand.LOW
    assert assessment.requires_immediate_review is True
    assert assessment.flagged_for_review is True
    assert "SAFETY ESCALATION" in assessment.explanation


def test_low_community_votes_never_suppress_serious_incident():
    """Zero or low community votes must never suppress a high severity incident."""
    # Critical danger (Severity 100) reported by only 1 person (Verification 0)
    # (0.40 * 100) + (0.25 * 0) + (0.20 * 20) + (0.15 * 10) = 40 + 0 + 4 + 1.5 = 45.5 (Moderate)
    assessment = calculate_priority(
        severity=100.0,
        verification=0.0,
        recency=20.0,
        affected_area=10.0,
    )

    assert assessment.score == 45.5
    assert assessment.band == PriorityBand.MODERATE
    # Must still be flagged because Severity >= 75
    assert assessment.requires_immediate_review is True
    assert "not suppressed by low community verification" in assessment.explanation


def test_non_serious_incident_not_flagged():
    """Standard non-severe incidents should not be flagged for emergency review."""
    assessment = calculate_priority(
        severity=50.0,
        verification=40.0,
        recency=50.0,
        affected_area=30.0,
        is_serious_incident=False,
    )

    assert assessment.requires_immediate_review is False
    assert assessment.flagged_for_review is False
    assert "SAFETY ESCALATION" not in assessment.explanation


# ==============================================================================
# Explanation & Serialization Tests
# ==============================================================================

def test_human_readable_explanation():
    """Explanation clearly communicates score, band, and component breakdown."""
    assessment = calculate_priority(70.0, 50.0, 60.0, 40.0)

    assert assessment.explanation
    assert "Calculated composite priority score" in assessment.explanation
    assert "High priority band" in assessment.explanation
    assert "Severity=" in assessment.explanation
    assert "Verification=" in assessment.explanation


def test_to_dict_serialization():
    """Assessment cleanly converts to dictionary for downstream consumers."""
    assessment = calculate_priority(60.0, 40.0, 50.0, 30.0)
    data = assessment.to_dict()

    assert isinstance(data, dict)
    assert data["score"] == 48.5
    assert data["band"] == "Moderate"
    assert data["severity"] == 60.0
    assert data["verification"] == 40.0
    assert data["recency"] == 50.0
    assert data["affected_area"] == 30.0
    assert data["requires_immediate_review"] is False
    assert data["flagged_for_review"] is False
    assert isinstance(data["explanation"], str)
