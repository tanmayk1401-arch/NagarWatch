"""Priority intelligence service for NagarWatch.

Calculates composite triage priority scores for hyperlocal incidents using a deterministic
formula based on incident severity, verification credibility, recency, and affected area.
Ensures safety-critical incidents are flagged for human review regardless of score or vote suppression.
"""

import math
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Dict


class PriorityBand(str, Enum):
    """Priority triage tiers for NagarWatch incidents."""

    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass(frozen=True)
class PriorityAssessment:
    """Standardized priority calculation assessment payload."""

    score: float
    band: PriorityBand
    severity: float
    verification: float
    recency: float
    affected_area: float
    requires_immediate_review: bool
    explanation: str

    @property
    def flagged_for_review(self) -> bool:
        """Alias for requires_immediate_review."""
        return self.requires_immediate_review

    def to_dict(self) -> Dict[str, Any]:
        """Convert assessment to JSON-serializable dictionary."""
        data = asdict(self)
        data["band"] = self.band.value
        data["flagged_for_review"] = self.flagged_for_review
        return data


class PriorityService:
    """Deterministic priority intelligence engine for NagarWatch."""

    # Exact weighting coefficients as mandated by NagarWatch intelligence formula:
    # Priority = (0.40 × Severity) + (0.25 × Verification) + (0.20 × Recency) + (0.15 × Affected Area)
    SEVERITY_WEIGHT: float = 0.40
    VERIFICATION_WEIGHT: float = 0.25
    RECENCY_WEIGHT: float = 0.20
    AFFECTED_AREA_WEIGHT: float = 0.15

    # Safety threshold: severity scores at or above this mark represent serious safety incidents
    SERIOUS_SEVERITY_THRESHOLD: float = 75.0

    @classmethod
    def validate_component(cls, name: str, value: Any) -> float:
        """Validate that an input component is a valid number within 0.0 to 100.0.

        Raises:
            TypeError: If input is not a float or integer.
            ValueError: If input is outside [0.0, 100.0] or is NaN/Infinity.
        """
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(
                f"Component '{name}' must be a numerical float or int, received {type(value).__name__}."
            )
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"Component '{name}' cannot be NaN or Infinite.")
        if value < 0.0 or value > 100.0:
            raise ValueError(
                f"Component '{name}' must be between 0.0 and 100.0, received {value}."
            )
        return float(value)

    @classmethod
    def determine_band(cls, score: float) -> PriorityBand:
        """Map composite score into standardized PriorityBand.

        Bands:
        - 0–29: Low
        - 30–49: Moderate
        - 50–74: High
        - 75–100: Critical
        """
        if score >= 75.0:
            return PriorityBand.CRITICAL
        if score >= 50.0:
            return PriorityBand.HIGH
        if score >= 30.0:
            return PriorityBand.MODERATE
        return PriorityBand.LOW

    @classmethod
    def calculate(
        cls,
        severity: float,
        verification: float,
        recency: float,
        affected_area: float,
        is_serious_incident: bool = False,
        **kwargs: Any,
    ) -> PriorityAssessment:
        """Calculate composite incident priority score and evaluation metadata.

        Args:
            severity: Assessed incident danger/severity score (0-100).
            verification: Community votes / verification corroboration score (0-100).
            recency: Time proximity / freshness score (0-100).
            affected_area: Geographic or population impact radius score (0-100).
            is_serious_incident: Explicit override flagging severe safety threats.
            **kwargs: Allows alias 'is_serious_safety_hazard'.

        Returns:
            PriorityAssessment containing score, band, components, review flag, and explanation.

        Raises:
            TypeError: If any input is not numerical.
            ValueError: If any input is outside 0.0-100.0 or NaN/Inf.
        """
        sev = cls.validate_component("severity", severity)
        ver = cls.validate_component("verification", verification)
        rec = cls.validate_component("recency", recency)
        area = cls.validate_component("affected_area", affected_area)

        # Calculate exact weighted composite score
        raw_score = (
            cls.SEVERITY_WEIGHT * sev
            + cls.VERIFICATION_WEIGHT * ver
            + cls.RECENCY_WEIGHT * rec
            + cls.AFFECTED_AREA_WEIGHT * area
        )

        # Protect against float arithmetic rounding artifacts
        clamped_score = max(0.0, min(100.0, raw_score))
        final_score = round(clamped_score, 2)

        band = cls.determine_band(final_score)

        # Safety escalation logic:
        # 1. Explicitly marked as a serious safety incident, OR
        # 2. High severity score (>= SERIOUS_SEVERITY_THRESHOLD)
        is_serious_flag = bool(
            is_serious_incident
            or kwargs.get("is_serious_safety_hazard", False)
            or sev >= cls.SERIOUS_SEVERITY_THRESHOLD
        )

        # Human-readable explanation
        explanation_parts = [
            f"Calculated composite priority score of {final_score:.2f} ({band.value} priority band) "
            f"based on weighted inputs: Severity={sev:.1f} (weight 40%), "
            f"Verification={ver:.1f} (weight 25%), Recency={rec:.1f} (weight 20%), "
            f"Affected Area={area:.1f} (weight 15%)."
        ]

        if is_serious_flag:
            if ver < 30.0:
                explanation_parts.append(
                    "SAFETY ESCALATION: Flagged for immediate human review. Serious safety hazards "
                    f"are not suppressed by low community verification ({ver:.1f}/100)."
                )
            else:
                explanation_parts.append(
                    "SAFETY ESCALATION: Flagged for immediate human review due to serious safety hazard."
                )

        explanation = " ".join(explanation_parts)

        return PriorityAssessment(
            score=final_score,
            band=band,
            severity=sev,
            verification=ver,
            recency=rec,
            affected_area=area,
            requires_immediate_review=is_serious_flag,
            explanation=explanation,
        )


def calculate_priority(
    severity: float,
    verification: float,
    recency: float,
    affected_area: float,
    is_serious_incident: bool = False,
    **kwargs: Any,
) -> PriorityAssessment:
    """Convenience functional wrapper around PriorityService.calculate."""
    return PriorityService.calculate(
        severity=severity,
        verification=verification,
        recency=recency,
        affected_area=affected_area,
        is_serious_incident=is_serious_incident,
        **kwargs,
    )
