"""AI Services integration layer for NagarWatch Django backend.

Connects the standalone ai_services package (classification, priority scoring,
duplicate detection, photo analysis, community assistant, and admin assistant)
to Django models (Issue, IssuePhoto, DuplicateCandidate, AIAnalysis, User).

Key Architectural Principles:
1. Pure Advisory Role: AI suggestions never automatically reject, delete, or merge reports.
2. Preserve Resident Data: The resident's original description and selected category are
   preserved verbatim without overwriting.
3. Graceful Fallback: Failures or timeouts in remote AI calls gracefully fall back to deterministic
   local rules without interrupting citizen report submission.
4. Documented Assumptions: Missing formulas (Verification, Recency, Affected Area curves)
   are documented transparently rather than invented.
"""

from datetime import datetime, timezone
import json
import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Union

from django.conf import settings
from django.utils import timezone as django_timezone

from ai_services.classification import IncidentClassifier
from ai_services.priority_service import PriorityService, PriorityBand, PriorityAssessment
from ai_services.duplicate_service import DuplicateService, DuplicateAssessment, detect_duplicates
from ai_services.photo_analysis import PhotoAnalyzer, PhotoAnalysisResult
from ai_services.community_assistant import CommunityAssistant, AssistantResponse, ask_community_assistant
from ai_services.admin_assistant import AdminAssistant, AdminAssistantResponse, ask_admin_assistant
from ai_services.schemas import IncidentCategory, IncidentSeverity, IncidentClassificationResult

from .models import Issue, IssuePhoto, DuplicateCandidate, AIAnalysis

logger = logging.getLogger(__name__)


# =====================================================================
# 1. CATEGORY & SEVERITY MAPPING HELPERS
# =====================================================================

VALID_CATEGORY_CHOICES = {c[0] for c in Issue.CATEGORY_CHOICES}
VALID_PRIORITY_CHOICES = {p[0] for p in Issue.PRIORITY_CHOICES}


def map_ai_category_to_choice(
    ai_category: Union[IncidentCategory, str],
    subcategory: str = "",
    text: str = "",
) -> str:
    """Map AI taxonomy categories safely to Issue.CATEGORY_CHOICES.

    Issue.CATEGORY_CHOICES:
    - "Roads & Footpaths"
    - "Streetlights"
    - "Water & Drainage"
    - "Garbage & Waste"
    - "Parks & Public Spaces"
    - "Other"
    """
    raw_cat = str(ai_category.value if hasattr(ai_category, "value") else ai_category).strip().lower()
    combined_ctx = f"{raw_cat} {(subcategory or '').lower()} {text.lower()}".strip()

    # 1. Traffic & Road Hazard
    if "traffic" in raw_cat or "road hazard" in raw_cat:
        return "Roads & Footpaths"

    # 2. Sanitation & Health
    if "sanitation" in raw_cat or "health" in raw_cat or "garbage" in raw_cat or "waste" in raw_cat:
        return "Garbage & Waste"

    # 3. Infrastructure (Disambiguate based on keywords and subcategory)
    if "infrastructure" in raw_cat:
        if any(w in combined_ctx for w in ["light", "lamp", "pole", "electric", "wire", "bulb", "dark", "wiring", "bescom"]):
            return "Streetlights"
        if any(w in combined_ctx for w in ["water", "drain", "sewer", "sewage", "pipe", "leak", "overflow", "gutter", "drainage", "bwssb", "flood"]):
            return "Water & Drainage"
        if any(w in combined_ctx for w in ["park", "garden", "playground", "bench", "tree"]):
            return "Parks & Public Spaces"
        if any(w in combined_ctx for w in ["pothole", "footpath", "road", "pavement", "sidewalk", "divider", "asphalt", "tar"]):
            return "Roads & Footpaths"
        return "Roads & Footpaths"

    # 4. Public Safety
    if "public safety" in raw_cat or "safety" in raw_cat:
        if any(w in combined_ctx for w in ["light", "lamp", "dark"]):
            return "Streetlights"
        if any(w in combined_ctx for w in ["park", "garden", "playground"]):
            return "Parks & Public Spaces"
        return "Other"

    # 5. Fire, Noise, Environmental, Other
    if any(w in raw_cat for w in ["fire", "environmental", "noise", "nuisance", "other"]):
        return "Other"

    # Fallback to direct match or "Other"
    for choice in Issue.CATEGORY_CHOICES:
        if raw_cat == choice[0].lower():
            return choice[0]

    return "Other"


def map_severity_to_choice(severity: Union[IncidentSeverity, str]) -> str:
    """Map AI severity levels (Low, Medium, High, Critical) to Issue.PRIORITY_CHOICES.

    Issue.PRIORITY_CHOICES:
    - "low"
    - "medium"
    - "high"
    - "urgent"
    """
    raw_sev = str(severity.value if hasattr(severity, "value") else severity).strip().lower()
    if raw_sev in ["critical", "urgent"]:
        return "urgent"
    if raw_sev in ["high"]:
        return "high"
    if raw_sev in ["medium", "moderate"]:
        return "medium"
    return "low"


def map_priority_band_to_choice(band: Union[PriorityBand, str]) -> str:
    """Map PriorityBand (Low, Moderate, High, Critical) to Issue.PRIORITY_CHOICES."""
    raw_band = str(band.value if hasattr(band, "value") else band).strip().lower()
    if raw_band == "critical":
        return "urgent"
    if raw_band == "high":
        return "high"
    if raw_band in ["moderate", "medium"]:
        return "medium"
    return "low"


# =====================================================================
# 2. PRIORITY SCORING ADAPTER (DOCUMENTED UNRESOLVED INPUTS)
# =====================================================================

def compute_priority_inputs(
    issue: Issue,
    classification_severity: Optional[str] = None,
    is_safety_critical: bool = False,
) -> Tuple[float, float, float, float, Dict[str, str]]:
    """Compute (Severity, Verification, Recency, AffectedArea) inputs on a 0-100 scale.

    Documents unresolved team inputs for Verification, Recency, and Affected Area.
    """
    # 1. Severity (0 - 100)
    sev_str = (classification_severity or issue.ai_severity or issue.priority or "medium").lower()
    severity_map = {
        "urgent": 100.0,
        "critical": 100.0,
        "high": 75.0,
        "medium": 50.0,
        "moderate": 50.0,
        "low": 25.0,
    }
    sev_score = severity_map.get(sev_str, 50.0)

    # 2. Verification (0 - 100)
    # UNRESOLVED INPUT: Team has not agreed on the curve formula for community vote weighting.
    # Implementation: Net positive community votes (upvotes - disputes) * 10, clamped to [0, 100].
    # Defaults to 0.0 for new submissions.
    net_votes = max(0, issue.upvotes - issue.disputes)
    ver_score = min(100.0, float(net_votes) * 10.0)

    # 3. Recency (0 - 100)
    # UNRESOLVED INPUT: Team has not agreed on the temporal decay half-life curve.
    # Implementation: Defaults to 100.0 for newly submitted reports (< 1 hour).
    # If occurred_at is provided, decays linearly across a 72-hour window to a floor of 10.0.
    ref_time = issue.occurred_at or issue.created_at or django_timezone.now()
    now = django_timezone.now()
    elapsed_hours = max(0.0, (now - ref_time).total_seconds() / 3600.0)
    if elapsed_hours <= 1.0:
        rec_score = 100.0
    else:
        rec_score = max(10.0, 100.0 - ((elapsed_hours / 72.0) * 90.0))

    # 4. Affected Area (0 - 100)
    # UNRESOLVED INPUT: Issue model currently lacks geographic radius or population density fields.
    # Implementation: Defaults to 50.0 (neutral baseline) until GIS ward-density service is integrated.
    area_score = 50.0

    documentation = {
        "severity_note": f"Derived from AI severity ({sev_str}) -> {sev_score}",
        "verification_formula": "Net community confirmations (upvotes - disputes) * 10 clamped to [0, 100]. Default 0.0 for new reports.",
        "recency_formula": "Linear decay over 72 hours from occurred_at/created_at, defaulting to 100.0 for new reports.",
        "affected_area_formula": "Fixed neutral baseline (50.0) pending GIS ward population data integration on Issue model.",
    }

    return (sev_score, ver_score, rec_score, area_score, documentation)


# =====================================================================
# 3. FULL ISSUE AI PIPELINE
# =====================================================================

def process_issue_ai_pipeline(issue: Issue, classifier: Optional[IncidentClassifier] = None) -> Dict[str, Any]:
    """Execute complete AI intake pipeline for an Issue report.

    Performs:
    1. Incident classification (Gemini or deterministic local fallback).
    2. Category mapping (Issue.CATEGORY_CHOICES) and severity mapping.
    3. Priority scoring using the 0.40S + 0.25V + 0.20R + 0.15A formula.
    4. Duplicate incident candidate detection (advisory, saved in DuplicateCandidate).
    5. Saves full analysis history into AIAnalysis models.

    Preserves resident's original description and category intact.
    """
    results: Dict[str, Any] = {}

    # -----------------------------------------------------------------
    # Step 1: Incident Classification
    # -----------------------------------------------------------------
    try:
        classifier_inst = classifier or IncidentClassifier()
        report_text = (issue.description or issue.title or "").strip()
        classification = classifier_inst.classify_incident(report_text)

        mapped_cat = map_ai_category_to_choice(
            classification.category,
            subcategory=classification.subcategory,
            text=report_text,
        )
        mapped_sev = map_severity_to_choice(classification.severity)

        issue.ai_category = mapped_cat
        issue.ai_confidence = int(round(classification.confidence * 100))
        issue.ai_severity = mapped_sev

        # Record AIAnalysis for classification
        source_val = (
            AIAnalysis.Source.GEMINI
            if classification.source == "gemini"
            else AIAnalysis.Source.FALLBACK
        )
        AIAnalysis.objects.create(
            issue=issue,
            service_name=AIAnalysis.ServiceName.CLASSIFICATION,
            result=classification.to_dict(),
            confidence=classification.confidence,
            source=source_val,
            model_name=getattr(classification, "model_name", "gemini-2.5-flash"),
        )
        results["classification"] = classification.to_dict()

    except Exception as e:
        logger.error(f"Classification failed for issue #{issue.pk}: {e}", exc_info=True)
        # Safe deterministic fallback values
        issue.ai_category = issue.category or "Other"
        issue.ai_confidence = 50
        issue.ai_severity = "medium"
        AIAnalysis.objects.create(
            issue=issue,
            service_name=AIAnalysis.ServiceName.CLASSIFICATION,
            result={"error": str(e), "status": "failed_safe_fallback"},
            confidence=0.5,
            source=AIAnalysis.Source.FALLBACK,
            model_name="safe_rule_fallback",
        )
        classification = None

    # -----------------------------------------------------------------
    # Step 2: Priority Calculation
    # -----------------------------------------------------------------
    try:
        is_critical_flag = (
            issue.ai_severity == "urgent"
            or (classification and classification.severity == IncidentSeverity.CRITICAL)
        )
        s, v, r, a, doc_notes = compute_priority_inputs(
            issue,
            classification_severity=issue.ai_severity,
            is_safety_critical=is_critical_flag,
        )

        priority_assessment = PriorityService.calculate(
            severity=s,
            verification=v,
            recency=r,
            affected_area=a,
            immediate_safety_hazard=is_critical_flag,
        )

        issue.priority_score = priority_assessment.score
        issue.priority = map_priority_band_to_choice(priority_assessment.band)

        # Update metadata with unresolved inputs documentation
        metadata = dict(issue.ai_metadata or {})
        metadata["priority_assessment"] = priority_assessment.to_dict()
        metadata["unresolved_inputs"] = doc_notes
        issue.ai_metadata = metadata

        AIAnalysis.objects.create(
            issue=issue,
            service_name=AIAnalysis.ServiceName.PRIORITY,
            result=priority_assessment.to_dict(),
            confidence=1.0,
            source=AIAnalysis.Source.RULE_BASED,
            model_name="deterministic_priority_v1",
        )
        results["priority"] = priority_assessment.to_dict()

    except Exception as e:
        logger.error(f"Priority calculation failed for issue #{issue.pk}: {e}", exc_info=True)
        issue.priority_score = 50.0
        issue.priority = "medium"

    # Save issue changes from Step 1 and 2
    issue.save(update_fields=[
        "ai_category",
        "ai_confidence",
        "ai_severity",
        "priority_score",
        "priority",
        "ai_metadata",
    ])

    # -----------------------------------------------------------------
    # Step 3: Duplicate Incident Detection
    # -----------------------------------------------------------------
    try:
        candidates = evaluate_issue_duplicates(issue)
        results["duplicate_candidates_count"] = len(candidates)
    except Exception as e:
        logger.error(f"Duplicate detection failed for issue #{issue.pk}: {e}", exc_info=True)
        results["duplicate_candidates_count"] = 0

    return results


def evaluate_issue_duplicates(issue: Issue) -> List[DuplicateCandidate]:
    """Scan existing open/active issues to detect potential duplicates.

    Thresholds:
    - Below 60: Separate incidents.
    - 60 - 79.99: Possible duplicate -> create DuplicateCandidate for human review.
    - 80 - 100: Strong duplicate -> create DuplicateCandidate and flag ai_is_duplicate.

    Strict Policy: Never automatically merge, delete, or reject reports.
    """
    created_candidates: List[DuplicateCandidate] = []

    # Query active/open issues excluding itself
    query = Issue.objects.exclude(pk=issue.pk).filter(
        status__in=["pending", "verified", "in_progress"]
    )

    issue_data = {
        "description": issue.description or issue.title,
        "category": issue.category,
        "timestamp": issue.occurred_at or issue.created_at,
        "latitude": issue.latitude,
        "longitude": issue.longitude,
    }

    highest_score = 0.0
    strongest_match: Optional[Issue] = None

    for existing in query[:50]:  # Cap to recent 50 active incidents for triage
        cand_data = {
            "description": existing.description or existing.title,
            "category": existing.category,
            "timestamp": existing.occurred_at or existing.created_at,
            "latitude": existing.latitude,
            "longitude": existing.longitude,
        }

        assessment: DuplicateAssessment = detect_duplicates(issue_data, cand_data)

        if assessment.score >= 60.0:
            dup_cand, _ = DuplicateCandidate.objects.update_or_create(
                issue=issue,
                candidate_issue=existing,
                defaults={
                    "similarity_score": round(assessment.score, 2),
                    "review_status": DuplicateCandidate.ReviewStatus.PENDING,
                    "evaluated_at": django_timezone.now(),
                },
            )
            created_candidates.append(dup_cand)

            if assessment.score > highest_score:
                highest_score = assessment.score
                if assessment.score >= 80.0:
                    strongest_match = existing

    # Advisory duplicate flag if strong candidate detected (never auto-merge/delete)
    if strongest_match:
        issue.ai_is_duplicate = True
        issue.ai_duplicate_of = strongest_match
        issue.save(update_fields=["ai_is_duplicate", "ai_duplicate_of"])

    if created_candidates:
        AIAnalysis.objects.create(
            issue=issue,
            service_name=AIAnalysis.ServiceName.DUPLICATE,
            result={
                "candidates_found": len(created_candidates),
                "highest_similarity": highest_score,
                "requires_human_review": True,
            },
            confidence=round(highest_score / 100.0, 2),
            source=AIAnalysis.Source.RULE_BASED,
            model_name="deterministic_duplicate_v1",
        )

    return created_candidates


# =====================================================================
# 4. PHOTO ANALYSIS INTEGRATION
# =====================================================================

def process_issue_photos(issue: Issue, analyzer: Optional[PhotoAnalyzer] = None) -> List[Dict[str, Any]]:
    """Analyze all saved photos for an issue using Gemini Vision.

    Advisory only: Never rejects reports based on photos.
    Updates IssuePhoto.ai_description, ai_confidence, and ai_metadata.
    """
    photos = issue.photos.all()
    results = []

    if not photos.exists():
        return results

    analyzer_inst = analyzer or PhotoAnalyzer()

    for photo in photos:
        try:
            image_path = photo.image.path
            res: PhotoAnalysisResult = analyzer_inst.analyze_photo(
                image=image_path,
                incident_description=issue.description or issue.title,
                claimed_category=issue.category,
            )

            photo.ai_description = res.visible_description
            photo.ai_confidence = res.confidence
            photo.ai_metadata = res.to_dict()
            photo.save(update_fields=["ai_description", "ai_confidence", "ai_metadata"])

            AIAnalysis.objects.create(
                issue=issue,
                service_name=AIAnalysis.ServiceName.PHOTO,
                result=res.to_dict(),
                confidence=res.confidence,
                source=AIAnalysis.Source.GEMINI,
                model_name=getattr(analyzer_inst, "model_name", "gemini-2.5-flash"),
            )
            results.append({"photo_id": photo.pk, "status": "success", "result": res.to_dict()})

        except Exception as e:
            logger.warning(f"Photo #{photo.pk} analysis failed or skipped: {e}")
            photo.ai_description = "Attached citizen photo (automated visual AI analysis unavailable)."
            photo.ai_confidence = 0.0
            photo.ai_metadata = {"notice": "Photo advisory only; analysis unavailable.", "error": str(e)}
            photo.save(update_fields=["ai_description", "ai_confidence", "ai_metadata"])
            results.append({"photo_id": photo.pk, "status": "fallback", "error": str(e)})

    return results


# =====================================================================
# 5. ASSISTANTS INTEGRATION (COMMUNITY & ADMIN)
# =====================================================================

def handle_community_assistant_query(
    query: str,
    user: Optional[Any] = None,
    issue_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Process a resident question with context injection and safety protocols."""
    context: Optional[Dict[str, Any]] = None

    if issue_id:
        try:
            issue = Issue.objects.get(pk=issue_id)
            context = {
                "report_id": issue.id_code or f"NW-{issue.pk}",
                "title": issue.title,
                "category": issue.category,
                "status": issue.get_status_display(),
                "priority": issue.get_priority_display(),
                "created_at": issue.created_at.strftime("%Y-%m-%d %H:%M UTC") if issue.created_at else None,
            }
        except Issue.DoesNotExist:
            pass

    response: AssistantResponse = ask_community_assistant(query=query, context=context)
    return response.to_dict()


def handle_admin_assistant_query(query: str, user: Optional[Any] = None) -> Dict[str, Any]:
    """Process an admin query using factual database statistics and Python calculations."""
    # Pull current factual data from Issue database
    issues_qs = Issue.objects.all().values("category", "status", "priority", "priority_score", "created_at")
    records: List[Dict[str, Any]] = []

    for item in issues_qs:
        records.append({
            "category": item.get("category", "Other"),
            "status": item.get("status", "pending"),
            "priority": item.get("priority", "medium"),
            "priority_score": item.get("priority_score", 50.0),
        })

    response: AdminAssistantResponse = ask_admin_assistant(query=query, data=records)
    return response.to_dict()

