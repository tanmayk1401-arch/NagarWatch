"""Duplicate incident detection service for NagarWatch.

Implements multi-signal duplicate triage across geographic proximity, category alignment,
temporal proximity, and textual similarity using a deterministic weighted formula:
    D = 0.40G + 0.25C + 0.15T + 0.20S

Adheres strictly to human-in-the-loop review policy: duplicate candidates require
human verification and are never automatically merged, deleted, or suppressed.
"""

import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from enum import Enum
from typing import Any, Dict, Optional, Tuple, Union


class DuplicateDecision(str, Enum):
    """Decision outcomes for duplicate incident triage."""

    SEPARATE = "Separate incidents."
    POSSIBLE_DUPLICATE = "Possible duplicate — human review required."
    STRONG_DUPLICATE = "Strong duplicate candidate — human review required."


@dataclass(frozen=True)
class DuplicateAssessment:
    """Standardized assessment payload returned by duplicate detection."""

    score: float
    decision: DuplicateDecision
    geographic_similarity: float
    category_similarity: float
    time_similarity: float
    text_similarity: float
    requires_human_review: bool
    explanation: str

    @property
    def g(self) -> float:
        """Alias for geographic_similarity."""
        return self.geographic_similarity

    @property
    def c(self) -> float:
        """Alias for category_similarity."""
        return self.category_similarity

    @property
    def t(self) -> float:
        """Alias for time_similarity."""
        return self.time_similarity

    @property
    def s(self) -> float:
        """Alias for text_similarity."""
        return self.text_similarity

    def to_dict(self) -> Dict[str, Any]:
        """Convert assessment to JSON-serializable dictionary."""
        data = asdict(self)
        data["decision"] = self.decision.value
        data["requires_human_review"] = self.requires_human_review
        return data


def haversine_distance_meters(
    coord1: Tuple[float, float],
    coord2: Tuple[float, float],
) -> float:
    """Calculate great-circle distance between two points in meters using Haversine formula."""
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    # Earth radius in meters
    r = 6371000.0

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def extract_coordinates(incident: Any) -> Optional[Tuple[float, float]]:
    """Safely extract latitude and longitude from dictionary or object.

    Returns (latitude, longitude) if valid, or None if missing or invalid.
    """
    if incident is None:
        return None

    lat: Optional[Any] = None
    lon: Optional[Any] = None

    if isinstance(incident, dict):
        lat = incident.get("latitude", incident.get("lat"))
        lon = incident.get("longitude", incident.get("lon", incident.get("lng")))
        if lat is None or lon is None:
            coords = incident.get("coordinates")
            if isinstance(coords, (list, tuple)) and len(coords) == 2:
                lat, lon = coords[0], coords[1]
    else:
        if hasattr(incident, "latitude") and hasattr(incident, "longitude"):
            lat = getattr(incident, "latitude")
            lon = getattr(incident, "longitude")
        elif hasattr(incident, "coordinates"):
            coords = getattr(incident, "coordinates")
            if isinstance(coords, (list, tuple)) and len(coords) == 2:
                lat, lon = coords[0], coords[1]

    if lat is None or lon is None:
        return None

    try:
        lat_f = float(lat)
        lon_f = float(lon)
        if math.isnan(lat_f) or math.isnan(lon_f) or math.isinf(lat_f) or math.isinf(lon_f):
            return None
        if -90.0 <= lat_f <= 90.0 and -180.0 <= lon_f <= 180.0:
            return (lat_f, lon_f)
    except (ValueError, TypeError):
        return None

    return None


def parse_timestamp(val: Any) -> Optional[datetime]:
    """Safely parse input into UTC timezone-aware datetime."""
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val.astimezone(timezone.utc)
    if isinstance(val, (int, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        try:
            return datetime.fromtimestamp(val, tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            return None
    if isinstance(val, str):
        val_str = val.strip()
        if not val_str:
            return None
        try:
            cleaned = val_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except (ValueError, TypeError):
            pass
        for fmt in (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d-%m-%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
        ):
            try:
                dt = datetime.strptime(val_str, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                continue
    return None


def calculate_geographic_similarity(
    coord1: Optional[Tuple[float, float]],
    coord2: Optional[Tuple[float, float]],
    max_radius_meters: float = 1000.0,
) -> float:
    """Calculate geographic similarity (0-100).

    Score is 100.0 at 0m distance, decaying linearly to 0.0 at max_radius_meters (default 1km).
    Returns 0.0 if either coordinate is missing.
    """
    if coord1 is None or coord2 is None:
        return 0.0
    dist = haversine_distance_meters(coord1, coord2)
    if dist <= 0.0:
        return 100.0
    if dist >= max_radius_meters:
        return 0.0
    similarity = 100.0 * (1.0 - (dist / max_radius_meters))
    return round(max(0.0, min(100.0, similarity)), 2)


def calculate_category_similarity(
    cat1: Optional[Any],
    cat2: Optional[Any],
) -> float:
    """Calculate category similarity (0-100).

    Returns 100.0 if categories match (case-insensitive string or enum),
    0.0 if categories differ or either is missing.
    """
    if cat1 is None or cat2 is None:
        return 0.0
    s1 = getattr(cat1, "value", str(cat1)).strip().lower()
    s2 = getattr(cat2, "value", str(cat2)).strip().lower()
    if not s1 or not s2:
        return 0.0
    return 100.0 if s1 == s2 else 0.0


def calculate_time_similarity(
    time1: Optional[Any],
    time2: Optional[Any],
    max_window_hours: float = 72.0,
) -> float:
    """Calculate temporal similarity (0-100).

    Score is 100.0 at 0s difference, decaying linearly to 0.0 at max_window_hours (default 72h).
    Returns 0.0 if either timestamp is missing or unparseable.
    """
    dt1 = parse_timestamp(time1)
    dt2 = parse_timestamp(time2)
    if dt1 is None or dt2 is None:
        return 0.0
    delta_seconds = abs((dt2 - dt1).total_seconds())
    max_seconds = max_window_hours * 3600.0
    if delta_seconds <= 0.0:
        return 100.0
    if delta_seconds >= max_seconds:
        return 0.0
    similarity = 100.0 * (1.0 - (delta_seconds / max_seconds))
    return round(max(0.0, min(100.0, similarity)), 2)


def calculate_text_similarity(
    text1: Optional[str],
    text2: Optional[str],
) -> float:
    """Calculate textual similarity (0-100) using difflib.SequenceMatcher."""
    if not text1 or not text2:
        return 0.0
    t1 = " ".join(str(text1).strip().lower().split())
    t2 = " ".join(str(text2).strip().lower().split())
    if not t1 or not t2:
        return 0.0
    ratio = SequenceMatcher(None, t1, t2).ratio()
    return round(ratio * 100.0, 2)


def determine_duplicate_decision(score: float) -> DuplicateDecision:
    """Map duplicate composite score to standardized decision threshold.

    Thresholds:
    - Below 60: Separate incidents.
    - 60–79.99: Possible duplicate — human review required.
    - 80–100: Strong duplicate candidate — human review required.
    """
    if score >= 80.0:
        return DuplicateDecision.STRONG_DUPLICATE
    if score >= 60.0:
        return DuplicateDecision.POSSIBLE_DUPLICATE
    return DuplicateDecision.SEPARATE


class DuplicateService:
    """NagarWatch Duplicate Incident Detection Service.

    Applies the weighted formula:
        D = 0.40G + 0.25C + 0.15T + 0.20S
    """

    WEIGHT_GEOGRAPHIC: float = 0.40
    WEIGHT_CATEGORY: float = 0.25
    WEIGHT_TIME: float = 0.15
    WEIGHT_TEXT: float = 0.20

    @classmethod
    def validate_component(cls, name: str, value: Any) -> float:
        """Validate component similarity score is a numerical value between 0.0 and 100.0."""
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
    def calculate_from_components(
        cls,
        geographic_similarity: float,
        category_similarity: float,
        time_similarity: float,
        text_similarity: float,
        missing_notes: Optional[str] = None,
    ) -> DuplicateAssessment:
        """Calculate duplicate score directly from four pre-computed component scores.

        Args:
            geographic_similarity: Geographic proximity score (0-100).
            category_similarity: Incident category match score (0-100).
            time_similarity: Temporal proximity score (0-100).
            text_similarity: Narrative text similarity score (0-100).
            missing_notes: Optional diagnostic notes regarding missing fields.

        Returns:
            DuplicateAssessment with overall score, decision, components, and explanation.

        Raises:
            TypeError: If any score is not numerical.
            ValueError: If any score is outside [0.0, 100.0] or NaN/Inf.
        """
        g = cls.validate_component("geographic_similarity", geographic_similarity)
        c = cls.validate_component("category_similarity", category_similarity)
        t = cls.validate_component("time_similarity", time_similarity)
        s = cls.validate_component("text_similarity", text_similarity)

        # Formula: D = 0.40G + 0.25C + 0.15T + 0.20S
        raw_score = (
            cls.WEIGHT_GEOGRAPHIC * g
            + cls.WEIGHT_CATEGORY * c
            + cls.WEIGHT_TIME * t
            + cls.WEIGHT_TEXT * s
        )
        clamped_score = max(0.0, min(100.0, raw_score))
        final_score = round(clamped_score, 2)

        decision = determine_duplicate_decision(final_score)
        requires_review = decision != DuplicateDecision.SEPARATE

        explanation_parts = [
            f"Duplicate score {final_score:.2f} ({decision.value}) "
            f"derived from: Geographic={g:.1f}% (weight 40%), Category={c:.1f}% (weight 25%), "
            f"Time={t:.1f}% (weight 15%), Text={s:.1f}% (weight 20%)."
        ]

        if missing_notes:
            explanation_parts.append(f"Data note: {missing_notes}.")

        if requires_review:
            explanation_parts.append(
                "Policy note: Incidents are never automatically merged or deleted; "
                "human dispatcher review is required."
            )

        return DuplicateAssessment(
            score=final_score,
            decision=decision,
            geographic_similarity=g,
            category_similarity=c,
            time_similarity=t,
            text_similarity=s,
            requires_human_review=requires_review,
            explanation=" ".join(explanation_parts),
        )

    @classmethod
    def compare(
        cls,
        incident_a: Any,
        incident_b: Any,
        max_radius_meters: float = 1000.0,
        max_window_hours: float = 72.0,
    ) -> DuplicateAssessment:
        """Compare two incident reports and return a full DuplicateAssessment.

        Accepts incident models, dictionaries, or custom objects containing
        description, category, timestamp, and coordinates/latitude/longitude.

        Args:
            incident_a: First incident dictionary or object.
            incident_b: Second incident dictionary or object.
            max_radius_meters: Geographic distance at which similarity reaches 0 (default 1000m).
            max_window_hours: Temporal delta at which similarity reaches 0 (default 72h).

        Returns:
            DuplicateAssessment containing score, decision, components, and explanation.
        """
        # Safely extract attributes from dict or object
        desc_a = incident_a.get("description") if isinstance(incident_a, dict) else getattr(incident_a, "description", None)
        desc_b = incident_b.get("description") if isinstance(incident_b, dict) else getattr(incident_b, "description", None)

        cat_a = incident_a.get("category") if isinstance(incident_a, dict) else getattr(incident_a, "category", None)
        cat_b = incident_b.get("category") if isinstance(incident_b, dict) else getattr(incident_b, "category", None)

        time_a = incident_a.get("timestamp") if isinstance(incident_a, dict) else getattr(incident_a, "timestamp", None)
        time_b = incident_b.get("timestamp") if isinstance(incident_b, dict) else getattr(incident_b, "timestamp", None)

        coord_a = extract_coordinates(incident_a)
        coord_b = extract_coordinates(incident_b)

        # Track missing data safely
        missing_items = []
        if coord_a is None or coord_b is None:
            missing_items.append("missing coordinates")
        if cat_a is None or cat_b is None:
            missing_items.append("missing category")
        if time_a is None or time_b is None:
            missing_items.append("missing timestamp")
        if not desc_a or not desc_b:
            missing_items.append("missing description")

        missing_notes = f"Incomplete signals ({', '.join(missing_items)})" if missing_items else None

        # Compute component similarities (0-100)
        g_score = calculate_geographic_similarity(coord_a, coord_b, max_radius_meters=max_radius_meters)
        c_score = calculate_category_similarity(cat_a, cat_b)
        t_score = calculate_time_similarity(time_a, time_b, max_window_hours=max_window_hours)
        s_score = calculate_text_similarity(desc_a, desc_b)

        return cls.calculate_from_components(
            geographic_similarity=g_score,
            category_similarity=c_score,
            time_similarity=t_score,
            text_similarity=s_score,
            missing_notes=missing_notes,
        )


def detect_duplicates(
    incident_a: Any,
    incident_b: Any,
    max_radius_meters: float = 1000.0,
    max_window_hours: float = 72.0,
) -> DuplicateAssessment:
    """Functional convenience wrapper around DuplicateService.compare."""
    return DuplicateService.compare(
        incident_a=incident_a,
        incident_b=incident_b,
        max_radius_meters=max_radius_meters,
        max_window_hours=max_window_hours,
    )
