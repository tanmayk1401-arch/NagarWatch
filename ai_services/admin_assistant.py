"""Admin Intelligence Assistant for NagarWatch.

Provides administrative intelligence, incident statistical summaries, category distributions,
priority triage metrics, and operational trends for civic managers and safety dispatchers.
Enforces strict factual integrity: all factual calculations are computed deterministically
in Python, and predictive crime forecasting or neighborhood stigmatization is strictly prohibited.
Supports English, Hindi, and Hinglish.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ai_services.community_assistant import detect_query_language
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
from ai_services.schemas import LanguageDetection

logger = logging.getLogger(__name__)

ADMIN_ASSISTANT_SYSTEM_PROMPT = """You are the NagarWatch Admin Intelligence Assistant.
Your audience consists of municipal engineers, city administrators, and emergency dispatch supervisors.

CRITICAL OPERATING POLICIES:
1. FACTUAL INTEGRITY (STRICT):
   - You MUST rely ONLY on the verified factual statistics computed and supplied in the prompt.
   - NEVER invent, extrapolate, or hallucinate incident counts, percentages, trends, or dates.
   - If data is empty or missing, explicitly state that insufficient data is available.

2. ETHICAL & ANALYTICAL BOUNDARIES:
   - NEVER make predictive crime claims (e.g. "crime will increase here", "predict criminal hotspot").
   - NEVER brand neighborhoods as "dangerous" or make unsupported stigmatizing claims.
   - Focus strictly on civic infrastructure, physical hazards, resource allocation, and triage throughput.

3. MULTILINGUAL SUPPORT:
   - Answer in the same language as the admin's query: English, Hindi (Devanagari), or Hinglish (Romanized Hindi).

OUTPUT FORMAT:
Return ONLY a valid JSON object matching:
{
  "summary": "<2-3 sentence executive briefing>",
  "key_insights": ["<actionable insight 1>", "<actionable insight 2>", "<actionable insight 3>"],
  "answer": "<Comprehensive natural language answer to the admin's query>",
  "limitations": ["<data limitation or boundary 1>"]
}
DO NOT include markdown code blocks or text outside the JSON object.
"""


def compute_factual_statistics(
    raw_data: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]]
) -> Dict[str, Any]:
    """Calculate factual statistics deterministically in Python.

    Supports raw incident lists or pre-computed statistical dictionaries.
    Guarantees no fabricated metrics.
    """
    if not raw_data:
        return {
            "total_incidents": 0,
            "status_counts": {},
            "category_counts": {},
            "priority_counts": {},
            "category_percentages": {},
            "priority_percentages": {},
            "resolution_rate_percent": 0.0,
            "critical_and_high_count": 0,
            "critical_and_high_percentage": 0.0,
            "is_empty": True,
        }

    # Case A: Pre-aggregated statistical dictionary
    if isinstance(raw_data, dict) and ("total_incidents" in raw_data or "category_breakdown" in raw_data or "status_breakdown" in raw_data):
        total = int(raw_data.get("total_incidents", 0))
        cat_counts = dict(raw_data.get("category_breakdown", raw_data.get("category_counts", {})))
        stat_counts = dict(raw_data.get("status_breakdown", raw_data.get("status_counts", {})))
        prio_counts = dict(raw_data.get("priority_breakdown", raw_data.get("priority_counts", {})))

        if total == 0 and cat_counts:
            total = sum(cat_counts.values())
        elif total == 0 and stat_counts:
            total = sum(stat_counts.values())

        cat_pcts = {
            k: round((v / total) * 100.0, 1) if total > 0 else 0.0
            for k, v in cat_counts.items()
        }
        prio_pcts = {
            k: round((v / total) * 100.0, 1) if total > 0 else 0.0
            for k, v in prio_counts.items()
        }

        resolved_count = stat_counts.get("Resolved", 0) + stat_counts.get("Closed", 0) + stat_counts.get("resolved", 0)
        res_rate = round((resolved_count / total) * 100.0, 1) if total > 0 else 0.0

        crit_high = prio_counts.get("Critical", 0) + prio_counts.get("High", 0) + prio_counts.get("critical", 0) + prio_counts.get("high", 0)
        crit_high_pct = round((crit_high / total) * 100.0, 1) if total > 0 else 0.0

        return {
            "total_incidents": total,
            "status_counts": stat_counts,
            "category_counts": cat_counts,
            "priority_counts": prio_counts,
            "category_percentages": cat_pcts,
            "priority_percentages": prio_pcts,
            "resolution_rate_percent": res_rate,
            "critical_and_high_count": crit_high,
            "critical_and_high_percentage": crit_high_pct,
            "is_empty": total == 0,
        }

    # Case B: Raw incident list
    records: List[Dict[str, Any]] = raw_data if isinstance(raw_data, list) else []
    total = len(records)
    if total == 0:
        return {
            "total_incidents": 0,
            "status_counts": {},
            "category_counts": {},
            "priority_counts": {},
            "category_percentages": {},
            "priority_percentages": {},
            "resolution_rate_percent": 0.0,
            "critical_and_high_count": 0,
            "critical_and_high_percentage": 0.0,
            "is_empty": True,
        }

    cat_counts: Dict[str, int] = {}
    stat_counts: Dict[str, int] = {}
    prio_counts: Dict[str, int] = {"Critical": 0, "High": 0, "Moderate": 0, "Low": 0}

    for rec in records:
        cat = str(rec.get("category", "Other") or "Other").strip()
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

        stat = str(rec.get("status", "Pending Triage") or "Pending Triage").strip()
        stat_counts[stat] = stat_counts.get(stat, 0) + 1

        # Priority handling (string band or numeric score)
        prio_val = rec.get("priority_band", rec.get("priority", rec.get("severity", "Moderate")))
        if isinstance(prio_val, (int, float)):
            if prio_val >= 75.0:
                prio_band = "Critical"
            elif prio_val >= 50.0:
                prio_band = "High"
            elif prio_val >= 30.0:
                prio_band = "Moderate"
            else:
                prio_band = "Low"
        else:
            prio_str = str(prio_val).strip().capitalize()
            prio_band = prio_str if prio_str in prio_counts else "Moderate"

        prio_counts[prio_band] += 1

    cat_pcts = {k: round((v / total) * 100.0, 1) for k, v in cat_counts.items()}
    prio_pcts = {k: round((v / total) * 100.0, 1) for k, v in prio_counts.items()}

    resolved_count = stat_counts.get("Resolved", 0) + stat_counts.get("Closed", 0)
    res_rate = round((resolved_count / total) * 100.0, 1)

    crit_high = prio_counts.get("Critical", 0) + prio_counts.get("High", 0)
    crit_high_pct = round((crit_high / total) * 100.0, 1)

    return {
        "total_incidents": total,
        "status_counts": stat_counts,
        "category_counts": cat_counts,
        "priority_counts": prio_counts,
        "category_percentages": cat_pcts,
        "priority_percentages": prio_pcts,
        "resolution_rate_percent": res_rate,
        "critical_and_high_count": crit_high,
        "critical_and_high_percentage": crit_high_pct,
        "is_empty": False,
    }


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


class RawAdminPayload(BaseModel):
    """Raw structured payload validated from Gemini administrative assistant."""

    model_config = ConfigDict(extra="ignore")

    summary: str = Field(..., min_length=5)
    key_insights: List[str] = Field(default_factory=list)
    answer: str = Field(..., min_length=5)
    limitations: List[str] = Field(default_factory=list)


class AdminAssistantResponse(BaseModel):
    """Structured response returned by the Admin Intelligence Assistant."""

    model_config = ConfigDict(frozen=True, use_enum_values=True)

    answer: str = Field(
        ...,
        description="Comprehensive natural language response tailored to administrative decision-makers."
    )
    summary: str = Field(
        ...,
        description="High-level executive briefing summarizing the dataset or query answer."
    )
    key_insights: List[str] = Field(
        default_factory=list,
        description="Actionable, bulleted insights extracted strictly from factual data."
    )
    statistics_used: Dict[str, Any] = Field(
        default_factory=dict,
        description="Factual numerical statistics computed deterministically in Python."
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Data limitations, sample boundaries, or unsupported analysis disclaimers."
    )
    source: str = Field(
        default="gemini",
        description="Inference source ('gemini' or 'local_fallback')."
    )
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC evaluation timestamp."
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to JSON-serializable dictionary."""
        return self.model_dump(mode="json")


class AdminAssistant:
    """Administrative intelligence assistant for NagarWatch civic managers."""

    def __init__(
        self,
        client: Optional[Any] = None,
        config: Optional[GeminiClientConfig] = None,
        fallback_enabled: bool = True,
    ) -> None:
        """Initialize AdminAssistant with optional client and config.

        Args:
            client: Optional pre-configured Gen AI client (enables mocking and DI).
            config: Optional GeminiClientConfig. Defaults to environment configuration.
            fallback_enabled: Whether to invoke deterministic local fallback when
                              Gemini times out or is temporarily unavailable.
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

    def ask(
        self,
        query: str,
        data: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
        fallback_enabled: Optional[bool] = None,
    ) -> AdminAssistantResponse:
        """Process an administrative query using verified factual data.

        Calculates factual statistics strictly in Python before invoking Gemini for
        natural language interpretation. Prevents hallucinated metrics and declines
        predictive crime/safety claims.

        Args:
            query: Administrative question or analysis request.
            data: Raw incident records list or pre-aggregated statistics dictionary.
            fallback_enabled: Optional per-call override for fallback behavior.

        Returns:
            AdminAssistantResponse with answer, summary, key_insights, statistics_used,
            limitations, and source.

        Raises:
            ValueError: If query is empty or not a string.
            GeminiTimeoutError: If remote API times out and fallback is disabled.
            GeminiAPIError: If upstream Gemini API fails and fallback is disabled.
            ClassificationValidationError: If model output is malformed and fallback is disabled.
        """
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Query must be a non-empty string.")

        clean_query = query.strip()
        use_fallback = self.fallback_enabled if fallback_enabled is None else fallback_enabled

        # Calculate factual numbers in Python (Requirement 3: Python, not Gemini)
        computed_stats = compute_factual_statistics(data)

        # Intercept unsupported predictive / ethical boundary violations
        if self._is_unsupported_analytical_query(clean_query):
            return self._build_unsupported_query_response(clean_query, computed_stats)

        # Build prompt embedding pre-calculated factual statistics
        prompt_parts = [
            f"Administrator Query: \"\"\"{clean_query}\"\"\"",
            f"Computed Factual Statistics (Backend Verified, DO NOT ALTER ANY NUMBER):\n{json.dumps(computed_stats, indent=2)}",
            "Synthesize an administrative briefing answering the query accurately according to the instructions."
        ]
        user_prompt = "\n\n".join(prompt_parts)

        try:
            call_kwargs: dict[str, Any] = {
                "model": self.config.model_name,
                "contents": user_prompt,
            }

            if types is not None:
                call_kwargs["config"] = types.GenerateContentConfig(
                    system_instruction=ADMIN_ASSISTANT_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.2,
                )

            response = self.client.models.generate_content(**call_kwargs)

        except TimeoutError as exc:
            if use_fallback:
                logger.warning("Gemini admin assistant timed out (%s). Using fallback.", exc)
                return self._fallback_reply(clean_query, computed_stats)
            raise GeminiTimeoutError(
                f"Gemini admin assistant timed out after {self.config.timeout_seconds}s.",
                details={"model": self.config.model_name, "error": str(exc)},
            ) from exc
        except Exception as exc:
            err_str = str(exc).lower()
            is_timeout = "timeout" in err_str or "deadline exceeded" in err_str or "504" in err_str
            is_unavailable = "unavailable" in err_str or "503" in err_str or "temporarily unavailable" in err_str

            if isinstance(exc, GeminiConfigurationError):
                raise

            if (is_timeout or is_unavailable) and use_fallback:
                logger.warning("Gemini admin assistant unavailable (%s). Using fallback.", exc)
                return self._fallback_reply(clean_query, computed_stats)

            if is_timeout:
                raise GeminiTimeoutError(
                    f"Gemini admin assistant timed out: {exc}",
                    details={"model": self.config.model_name, "error": str(exc)},
                ) from exc
            if not use_fallback:
                raise GeminiAPIError(
                    f"Google Gemini API error during admin assistant: {exc}",
                    details={"model": self.config.model_name, "error": str(exc)},
                ) from exc

            logger.warning("Gemini API error (%s). Using deterministic fallback.", exc)
            return self._fallback_reply(clean_query, computed_stats)

        # Validate response
        response_text = getattr(response, "text", None)
        if not response_text or not response_text.strip():
            if use_fallback:
                return self._fallback_reply(clean_query, computed_stats)
            raise ClassificationValidationError(
                "Gemini admin assistant returned an empty or null response.",
                details={"model": self.config.model_name},
            )

        cleaned_json = _clean_json_output(response_text)

        try:
            payload = RawAdminPayload.model_validate_json(cleaned_json)
        except Exception as exc:
            if use_fallback:
                return self._fallback_reply(clean_query, computed_stats)
            raise ClassificationValidationError(
                f"Admin assistant response failed Pydantic schema validation: {exc}",
                details={"raw_output": cleaned_json, "error": str(exc)},
            ) from exc

        # Ensure limitations reflect missing data if applicable
        limitations = list(payload.limitations)
        if computed_stats.get("is_empty", False):
            limitations.append("No incident records were provided; summary reflects empty dataset.")

        return AdminAssistantResponse(
            answer=payload.answer,
            summary=payload.summary,
            key_insights=payload.key_insights,
            statistics_used=computed_stats,
            limitations=limitations,
            source="gemini",
            evaluated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _is_unsupported_analytical_query(text: str) -> bool:
        """Identify requests asking for crime predictions, criminal profiling, or neighborhood stigmatization."""
        t = text.lower()
        if "predict" in t and ("crime" in t or "incident" in t or "future" in t):
            return True
        if "dangerous" in t and ("neighborhood" in t or "area" in t or "colony" in t or "ward" in t or "city" in t):
            return True
        if "unsafe" in t and ("neighborhood" in t or "area" in t or "colony" in t or "ward" in t or "city" in t):
            return True
        unsupported_markers = [
            "predict crime", "future crime", "predict where crime will happen",
            "most dangerous", "unsafe area", "criminal hotspot", "crime prediction",
            "अपराध की भविष्यवाणी", "सबसे खतरनाक"
        ]
        return any(marker in t for marker in unsupported_markers)

    @classmethod
    def _build_unsupported_query_response(
        cls,
        query: str,
        stats: Dict[str, Any],
    ) -> AdminAssistantResponse:
        """Decline requests for crime forecasting or neighborhood stigmatization."""
        lang = detect_query_language(query)

        if lang == LanguageDetection.HINDI:
            summary = "नीतिगत सीमा: अपराध की भविष्यवाणी या इलाके को 'खतरनाक' करार देने का अनुरोध अस्वीकार किया गया।"
            answer = (
                "नगरवॉच प्रशासनिक सहायक अपराध पूर्वानुमान (predictive crime forecasting) या किसी इलाके को "
                "असुरक्षित घोषित करने वाले दावों का समर्थन नहीं करता। हमारा प्लेटफॉर्म केवल सत्यापित नागरिक समस्याओं, "
                "बुनियादी ढांचे की मरम्मत, और सुरक्षा रिपोर्टों के तथ्यात्मक विश्लेषण पर केंद्रित है।"
            )
            insights = [
                "नागरिक सुरक्षा मंच अपराध पूर्वानुमान की अनुमति नहीं देता।",
                "विश्लेषण केवल सत्यापित ऐतिहासिक व वर्तमान रिपोर्टों तक सीमित है।"
            ]
        elif lang == LanguageDetection.HINGLISH:
            summary = "Policy boundary: Predictive crime forecasting aur neighborhood stigmatization allowed nahi hai."
            answer = (
                "NagarWatch Admin Assistant crime prediction ya kisi neighborhood ko 'dangerous' label karne wale claims "
                "support nahi karta. Hamara platform strictly verified civic hazards, infrastructure triage, aur factual "
                "dispatch records par focus karta hai."
            )
            insights = [
                "NagarWatch policy predictive crime forecasting ko prohibit karti hai.",
                "Analytics factual infrastructure aur reported civic data tak restricted hain."
            ]
        else:
            summary = "Policy boundary: Predictive crime forecasting and subjective area stigmatization are strictly prohibited."
            answer = (
                "NagarWatch does not make predictive crime forecasts or unsupported claims designating neighborhoods "
                "as 'dangerous'. Our administrative intelligence is strictly confined to verified civic hazards, "
                "infrastructure maintenance triage, and factual dispatch metrics."
            )
            insights = [
                "Predictive crime forecasting is out of scope and prohibited by NagarWatch ethics policy.",
                "Analytics are restricted strictly to factual, verified civic incident reporting."
            ]

        return AdminAssistantResponse(
            answer=answer,
            summary=summary,
            key_insights=insights,
            statistics_used=stats,
            limitations=["Declined predictive crime modeling and subjective area stigmatization."],
            source="local_fallback",
            evaluated_at=datetime.now(timezone.utc),
        )

    @classmethod
    def _fallback_reply(
        cls,
        query: str,
        stats: Dict[str, Any],
    ) -> AdminAssistantResponse:
        """Deterministic local fallback synthesizing administrative briefings directly from factual Python stats."""
        lang = detect_query_language(query)
        total = stats.get("total_incidents", 0)
        is_empty = stats.get("is_empty", True)

        # 1. Empty dataset handling
        if is_empty or total == 0:
            if lang == LanguageDetection.HINDI:
                summary = "विश्लेषण के लिए कोई डेटा उपलब्ध नहीं कराया गया।"
                answer = "वर्तमान में कोई घटना डेटा प्राप्त नहीं हुआ है। तथ्यात्मक सारांश या श्रेणी विश्लेषण के लिए कृपया डेटा प्रदान करें।"
                insights = ["डेटासेट खाली है (0 घटनाएं दर्ज)।"]
            elif lang == LanguageDetection.HINGLISH:
                summary = "Analysis ke liye koi data supply nahi kiya gaya."
                answer = "Filhal koi incident data provide nahi kiya gaya hai. Factual summary aur trends ke liye incident records provide karein."
                insights = ["Dataset empty hai (0 incidents recorded)."]
            else:
                summary = "No incident records provided for statistical analysis."
                answer = "No incident data was supplied. To generate incident summaries, category distributions, or priority trends, please provide incident records."
                insights = ["Dataset is empty (0 incidents recorded)."]

            return AdminAssistantResponse(
                answer=answer,
                summary=summary,
                key_insights=insights,
                statistics_used=stats,
                limitations=["No data was supplied; no statistics were fabricated."],
                source="local_fallback",
                evaluated_at=datetime.now(timezone.utc),
            )

        cat_counts = stats.get("category_counts", {})
        stat_counts = stats.get("status_counts", {})
        prio_counts = stats.get("priority_counts", {})
        crit_high = stats.get("critical_and_high_count", 0)
        crit_high_pct = stats.get("critical_and_high_percentage", 0.0)
        res_rate = stats.get("resolution_rate_percent", 0.0)

        # Find top category
        top_cat = max(cat_counts.items(), key=lambda x: x[1])[0] if cat_counts else "General"
        top_cat_count = cat_counts.get(top_cat, 0)
        top_cat_pct = stats.get("category_percentages", {}).get(top_cat, 0.0)

        pending_count = stat_counts.get("Pending Triage", 0) + stat_counts.get("Submitted", 0) + stat_counts.get("Pending", 0)
        in_progress_count = stat_counts.get("In Progress", 0) + stat_counts.get("Under Review", 0)
        resolved_count = stat_counts.get("Resolved", 0) + stat_counts.get("Closed", 0)

        # Format insights
        if lang == LanguageDetection.HINDI:
            summary = f"कुल {total} घटनाएं दर्ज हैं। प्रमुख श्रेणी '{top_cat}' है ({top_cat_pct}%) और समाधान दर {res_rate}% है।"
            insights = [
                f"कुल {total} घटनाओं में से {crit_high} ({crit_high_pct}%) Critical/High प्राथमिकता में हैं।",
                f"शीर्ष श्रेणी: {top_cat} ({top_cat_count} रिपोर्ट, {top_cat_pct}%)।",
                f"स्थिति ब्रेकडाउन: {pending_count} लंबित, {in_progress_count} प्रक्रियाधीन, {resolved_count} हल।"
            ]
            answer = (
                f"प्रशासनिक विश्लेषण सारांश:\n"
                f"- कुल दर्ज मामले: {total}\n"
                f"- प्रमुख श्रेणी: {top_cat} ({top_cat_pct}%)\n"
                f"- उच्च व गंभीर प्राथमिकता: {crit_high} मामले ({crit_high_pct}%)\n"
                f"- समाधान दर: {res_rate}% ({resolved_count} मामले हल)\n"
                f"- लंबित एवं प्रक्रियाधीन मामले: {pending_count + in_progress_count}"
            )
        elif lang == LanguageDetection.HINGLISH:
            summary = f"Total {total} incidents recorded hain. Leading category '{top_cat}' ({top_cat_pct}%) hai, overall resolution rate {res_rate}% hai."
            insights = [
                f"{total} total incidents me se {crit_high} ({crit_high_pct}%) Critical/High priority band me hain.",
                f"Top category: {top_cat} ({top_cat_count} reports, {top_cat_pct}%).",
                f"Status overview: {pending_count} pending, {in_progress_count} in-progress, {resolved_count} resolved."
            ]
            answer = (
                f"Administrative Summary Overview:\n"
                f"- Total Recorded Incidents: {total}\n"
                f"- Primary Category: {top_cat} ({top_cat_pct}% of total)\n"
                f"- Critical & High Priority: {crit_high} incidents ({crit_high_pct}%)\n"
                f"- Overall Resolution Rate: {res_rate}%\n"
                f"- Active Queue (Pending & In-Progress): {pending_count + in_progress_count} incidents"
            )
        else:
            summary = (
                f"Administrative analysis across {total} recorded incidents. "
                f"'{top_cat}' represents the primary domain ({top_cat_pct}%), with an overall {res_rate}% resolution rate."
            )
            insights = [
                f"{crit_high} of {total} incidents ({crit_high_pct}%) are categorized as Critical or High priority.",
                f"Leading operational category is '{top_cat}' with {top_cat_count} reports ({top_cat_pct}%).",
                f"Workflow status: {pending_count} pending triage, {in_progress_count} in-progress, {resolved_count} resolved ({res_rate}%)."
            ]
            answer = (
                f"Executive Incident Intelligence Summary:\n"
                f"1. Total Incident Volume: {total} verified reports.\n"
                f"2. Category Distribution: Leading category is '{top_cat}' with {top_cat_count} reports ({top_cat_pct}%).\n"
                f"3. Priority Escalation: {crit_high} incidents ({crit_high_pct}%) require urgent dispatch (Critical/High).\n"
                f"4. Dispatch & Resolution: {resolved_count} resolved ({res_rate}%), {in_progress_count} in-progress, {pending_count} pending triage."
            )

        return AdminAssistantResponse(
            answer=answer,
            summary=summary,
            key_insights=insights,
            statistics_used=stats,
            limitations=["Statistics computed strictly from provided sample dataset."],
            source="local_fallback",
            evaluated_at=datetime.now(timezone.utc),
        )


def ask_admin_assistant(
    query: str,
    data: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None,
    client: Optional[Any] = None,
    config: Optional[GeminiClientConfig] = None,
    fallback_enabled: bool = True,
) -> AdminAssistantResponse:
    """Convenience functional wrapper around AdminAssistant."""
    assistant = AdminAssistant(client=client, config=config, fallback_enabled=fallback_enabled)
    return assistant.ask(query=query, data=data)
