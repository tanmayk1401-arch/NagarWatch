"""Multilingual Community Assistant for NagarWatch.

Conversational assistant for residents providing guidance on incident reporting,
priority levels, report lifecycle statuses, platform navigation, and emergency protocols.
Supports English, Hindi, and Hinglish. Adheres to strict privacy, anti-hallucination,
and emergency escalation policies without direct database coupling.
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

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

COMMUNITY_ASSISTANT_SYSTEM_PROMPT = """You are the Multilingual Community Safety Assistant for NagarWatch – a Hyperlocal Community Safety Platform.
Your mission is to help residents understand how to report incidents, explain platform priority levels and statuses, and assist with civic safety guidance in their preferred language.

### CORE OPERATING RULES:
1. MULTILINGUAL SUPPORT:
   - Detect the language of the resident's query: English, Hindi (Devanagari), or Hinglish (Romanized Hindi).
   - ALWAYS respond in the SAME language/dialect used by the resident (Hindi in Hindi, Hinglish in Hinglish, English in English).

2. SAFETY & EMERGENCY POLICY:
   - If the resident describes an active, life-threatening emergency (fire, active crime, severe medical emergency, gas leak), immediately instruct them to contact local emergency services (Dial 112 / 100 for Police, 101 for Fire, 102 for Ambulance) without delay. Explain that NagarWatch is for community reporting, NOT emergency dispatch.

3. PRIVACY & DATA INTEGRITY (CRITICAL):
   - NEVER invent or hallucinate incident records, report numbers, ticket statuses, locations, or civic statistics.
   - If authorized context is NOT supplied in the prompt, clearly state that you do not have access to specific report records or live incident databases.
   - NEVER reveal personal information, contact numbers, or private details of other residents.
   - NEVER claim to have taken actions such as modifying, submitting, or deleting a report.

4. PLATFORM GUIDANCE:
   - Explaining how to report: Clear description of the hazard, category, location/landmarks, and photos if safe to capture.
   - Priority levels: Low (0-29), Moderate (30-49), High (50-74), Critical (75-100).
   - Report statuses: Submitted/Pending Triage -> Under Review -> In Progress / Dispatched -> Resolved -> Closed.
   - For off-topic or unrelated questions, politely clarify that NagarWatch Assistant is dedicated to hyperlocal safety and civic reporting.

### OUTPUT FORMAT:
You MUST respond ONLY with a raw JSON object matching:
{
  "answer": "<Your helpful, polite response in the resident's language>",
  "detected_language": "<English | Hindi | Hinglish | Other>",
  "confidence": <float between 0.0 and 1.0>,
  "requires_database_data": <true | false>,
  "limitations": ["<constraint or limitation note>"]
}
DO NOT include markdown code blocks or text outside the JSON object.
"""


def detect_query_language(text: str) -> LanguageDetection:
    """Detect language of resident query as English, Hindi, or Hinglish."""
    # 1. Hindi: Contains Devanagari Unicode characters (\u0900 - \u097F)
    if re.search(r"[\u0900-\u097F]", text):
        return LanguageDetection.HINDI

    # 2. Hinglish: Check for Romanized Hindi / Urdu keywords
    tokens = set(re.findall(r"[a-zA-Z]+", text.lower()))
    hinglish_markers = {
        "kya", "hai", "hain", "kaise", "kare", "karein", "batao", "mujhe",
        "meri", "mera", "mere", "kab", "hoga", "hogi", "nahi", "nahin",
        "pichhle", "din", "gali", "sadak", "paani", "pani", "aur", "ka",
        "ki", "ke", "ko", "par", "pe", "se", "yeh", "woh", "kuch",
        "karo", "raha", "rahi", "rahe", "tha", "thi", "the", "kharab",
        "gaddha", "kooda", "andhera", "chhedchhad", "chori", "shor", "ladai",
        "jhagda", "awaz", "bhai", "log", "kripya", "jaldi", "madad", "aag", "kitne"
    }
    strong_hinglish = {
        "kaise", "karein", "batao", "mujhe", "meri", "mera", "mere",
        "kharab", "andhera", "gaddha", "kooda", "sadak", "gali", "aag", "kitne"
    }
    if len(tokens.intersection(hinglish_markers)) >= 2 or any(t in strong_hinglish for t in tokens):
        return LanguageDetection.HINGLISH

    return LanguageDetection.ENGLISH


def build_assistant_prompt(
    query: str,
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Format resident query and authorized context for Gemini."""
    prompt_parts = [f"Resident Query: \"\"\"{query.strip()}\"\"\""]
    if context:
        prompt_parts.append(f"Authorized Backend Context:\n{json.dumps(context, indent=2)}")
    else:
        prompt_parts.append("Authorized Backend Context: None provided (No live database context available).")
    prompt_parts.append("Analyze the resident query and provide the required JSON response.")
    return "\n\n".join(prompt_parts)


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


class RawAssistantPayload(BaseModel):
    """Raw structured payload validated from Gemini assistant output."""

    model_config = ConfigDict(extra="ignore")

    answer: str = Field(..., min_length=2)
    detected_language: LanguageDetection = Field(default=LanguageDetection.ENGLISH)
    confidence: float = Field(..., ge=0.0, le=1.0)
    requires_database_data: bool = Field(default=False)
    limitations: List[str] = Field(default_factory=list)

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Confidence score must be in range [0.0, 1.0], received {v}")
        return round(v, 4)


class AssistantResponse(BaseModel):
    """Structured response returned by the Multilingual Community Assistant."""

    model_config = ConfigDict(frozen=True, use_enum_values=True)

    answer: str = Field(
        ...,
        description="Natural-language response delivered to the resident in their language."
    )
    detected_language: LanguageDetection = Field(
        ...,
        description="Detected language of user query (English, Hindi, or Hinglish)."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score in the response and intent matching."
    )
    requires_database_data: bool = Field(
        default=False,
        description="Whether answering this question requires live backend/database access."
    )
    source: str = Field(
        default="gemini",
        description="Generation source ('gemini' or 'local_fallback')."
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Known constraints, disclaimers, or data availability boundaries."
    )
    evaluated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when evaluation occurred."
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return self.model_dump(mode="json")


class CommunityAssistant:
    """Multilingual conversational assistant for NagarWatch residents."""

    def __init__(
        self,
        client: Optional[Any] = None,
        config: Optional[GeminiClientConfig] = None,
        fallback_enabled: bool = True,
    ) -> None:
        """Initialize Community Assistant with optional client and config.

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
        context: Optional[Dict[str, Any]] = None,
        fallback_enabled: Optional[bool] = None,
    ) -> AssistantResponse:
        """Process a resident question and return a structured natural language answer.

        Preserves user language (English, Hindi, Hinglish), respects privacy constraints,
        escalates emergencies, and refuses to fabricate database records.

        Args:
            query: Resident message or question.
            context: Optional authorized backend context (e.g. specific incident record).
            fallback_enabled: Optional per-call override for fallback behavior.

        Returns:
            AssistantResponse with answer, detected_language, confidence,
            requires_database_data, source, and limitations.

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

        # Check for immediate emergency triggers
        if self._is_emergency_query(clean_query):
            return self._build_emergency_response(clean_query)

        user_prompt = build_assistant_prompt(clean_query, context=context)

        try:
            call_kwargs: dict[str, Any] = {
                "model": self.config.model_name,
                "contents": user_prompt,
            }

            if types is not None:
                call_kwargs["config"] = types.GenerateContentConfig(
                    system_instruction=COMMUNITY_ASSISTANT_SYSTEM_PROMPT,
                    response_mime_type="application/json",
                    temperature=0.2,
                )

            response = self.client.models.generate_content(**call_kwargs)

        except TimeoutError as exc:
            if use_fallback:
                logger.warning("Gemini community assistant timed out (%s). Using fallback.", exc)
                return self._fallback_reply(clean_query, context=context)
            raise GeminiTimeoutError(
                f"Gemini community assistant timed out after {self.config.timeout_seconds}s.",
                details={"model": self.config.model_name, "error": str(exc)},
            ) from exc
        except Exception as exc:
            err_str = str(exc).lower()
            is_timeout = "timeout" in err_str or "deadline exceeded" in err_str or "504" in err_str
            is_unavailable = "unavailable" in err_str or "503" in err_str or "temporarily unavailable" in err_str

            if isinstance(exc, GeminiConfigurationError):
                raise

            if (is_timeout or is_unavailable) and use_fallback:
                logger.warning("Gemini community assistant unavailable (%s). Using fallback.", exc)
                return self._fallback_reply(clean_query, context=context)

            if is_timeout:
                raise GeminiTimeoutError(
                    f"Gemini community assistant timed out: {exc}",
                    details={"model": self.config.model_name, "error": str(exc)},
                ) from exc
            if not use_fallback:
                raise GeminiAPIError(
                    f"Google Gemini API error during community assistant: {exc}",
                    details={"model": self.config.model_name, "error": str(exc)},
                ) from exc

            logger.warning("Gemini API error (%s). Using deterministic fallback.", exc)
            return self._fallback_reply(clean_query, context=context)

        # Extract and validate response
        response_text = getattr(response, "text", None)
        if not response_text or not response_text.strip():
            if use_fallback:
                return self._fallback_reply(clean_query, context=context)
            raise ClassificationValidationError(
                "Gemini assistant returned an empty or null response.",
                details={"model": self.config.model_name},
            )

        cleaned_json = _clean_json_output(response_text)

        try:
            payload = RawAssistantPayload.model_validate_json(cleaned_json)
        except Exception as exc:
            if use_fallback:
                return self._fallback_reply(clean_query, context=context)
            raise ClassificationValidationError(
                f"Assistant response failed Pydantic schema validation: {exc}",
                details={"raw_output": cleaned_json, "error": str(exc)},
            ) from exc

        return AssistantResponse(
            answer=payload.answer,
            detected_language=payload.detected_language,
            confidence=payload.confidence,
            requires_database_data=payload.requires_database_data,
            source="gemini",
            limitations=payload.limitations,
            evaluated_at=datetime.now(timezone.utc),
        )

    @staticmethod
    def _is_emergency_query(text: str) -> bool:
        """Identify immediate physical life-safety emergencies."""
        t = text.lower()
        emergency_indicators = [
            "heart attack", "chest pain", "bleeding profusely", "someone collapsed",
            "house on fire", "building on fire", "fire right now", "aag lagi hai",
            "active robbery", "burglary in progress", "active shooter", "knife attack",
            "urgent ambulance", "ambulance jaldi", "police bulao", "call 112",
            "emergency help", "आग लगी है", "तुरंत एंबुलेंस", "पुलिस बुलाओ", "खून बह रहा"
        ]
        return any(ind in t for ind in emergency_indicators)

    @classmethod
    def _build_emergency_response(cls, query: str) -> AssistantResponse:
        """Generate immediate emergency protocol advisory."""
        lang = detect_query_language(query)
        if lang == LanguageDetection.HINDI:
            answer = (
                "आपातकालीन सूचना: यदि आप किसी तत्काल आपात स्थिति (आग, गंभीर चोट, सक्रिय अपराध) में हैं, "
                "तो कृपया तुरंत आपातकालीन सेवाओं (112 पर कॉल करें, या 100 पुलिस, 101 अग्निशमन, 102 एम्बुलेंस) "
                "से संपर्क करें। नगरवॉच एक नागरिक समस्या समाधान मंच है और यह आपातकालीन सेवाओं का विकल्प नहीं है।"
            )
        elif lang == LanguageDetection.HINGLISH:
            answer = (
                "EMERGENCY NOTICE: Agar aap kisi active emergency (aag, severe injury, ya crime) me hain, "
                "to bina der kiye turant emergency services ko dial karein (112 National Emergency, ya 100 Police, "
                "101 Fire, 102 Ambulance). NagarWatch civic reporting platform hai aur emergency dispatch ka substitute nahi hai."
            )
        else:
            answer = (
                "EMERGENCY NOTICE: If you are experiencing an active life-threatening emergency (fire, severe injury, "
                "or active crime), please immediately dial emergency services (Call 112, 100 for Police, 101 for Fire, "
                "or 102 for Ambulance). NagarWatch is a civic triage platform and is NOT an emergency dispatch service."
            )

        return AssistantResponse(
            answer=answer,
            detected_language=lang,
            confidence=1.0,
            requires_database_data=False,
            source="local_fallback",
            limitations=["Immediate safety escalation: Directed resident to public emergency dispatchers."],
            evaluated_at=datetime.now(timezone.utc),
        )

    @classmethod
    def _fallback_reply(
        cls,
        query: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> AssistantResponse:
        """Deterministic local fallback for resident queries when Gemini is unavailable."""
        lang = detect_query_language(query)
        q_lower = query.lower()

        # 1. Privacy inquiries: Requesting another resident's info
        if any(k in q_lower for k in ["who reported", "reporter name", "phone number", "kisne report kiya", "किसने शिकायत की", "reporter phone"]):
            if lang == LanguageDetection.HINDI:
                answer = "सामुदायिक सुरक्षा और गोपनीयता के लिए, नगरवॉच शिकायतकर्ताओं की पहचान गोपनीय रखता है और व्यक्तिगत जानकारी साझा नहीं करता।"
            elif lang == LanguageDetection.HINGLISH:
                answer = "Community safety aur privacy protect karne ke liye, NagarWatch reporter identities ko strictly confidential rakhta hai aur personal details share nahi karta."
            else:
                answer = "To protect community safety and privacy, NagarWatch strictly anonymizes reporter identities and does not share personal resident contact information."

            return AssistantResponse(
                answer=answer,
                detected_language=lang,
                confidence=0.95,
                requires_database_data=False,
                source="local_fallback",
                limitations=["Privacy policy prohibits disclosing personal details or third-party resident reports."],
                evaluated_at=datetime.now(timezone.utc),
            )

        # 2. Specific report status / database inquiries
        db_indicators = [
            "my report", "status of report", "ticket", "meri report", "status kya hai",
            "report id", "report #", "kitne pothole", "how many reports", "रिपोर्ट स्टेटस", "मेरी रिपोर्ट"
        ]
        if any(k in q_lower for k in db_indicators):
            if context and ("status" in context or "report_id" in context):
                # Context is authorized and provided
                rep_id = context.get("report_id", "your report")
                st = context.get("status", "Under Review")
                cat = context.get("category", "Civic Issue")
                if lang == LanguageDetection.HINDI:
                    answer = f"आपकी रिपोर्ट #{rep_id} वर्तमान में '{st}' स्थिति में है (श्रेणी: {cat})।"
                elif lang == LanguageDetection.HINGLISH:
                    answer = f"Aapki report #{rep_id} currently '{st}' status me hai (Category: {cat})."
                else:
                    answer = f"Your report #{rep_id} is currently '{st}' (Category: {cat})."

                return AssistantResponse(
                    answer=answer,
                    detected_language=lang,
                    confidence=0.95,
                    requires_database_data=True,
                    source="local_fallback",
                    limitations=["Status derived from provided backend context; verify with live dashboard."],
                    evaluated_at=datetime.now(timezone.utc),
                )

            # Context is NOT provided: Never hallucinate!
            if lang == LanguageDetection.HINDI:
                answer = (
                    "वर्तमान में मेरे पास आपके व्यक्तिगत रिपोर्ट रिकॉर्ड या लाइव डेटाबेस का एक्सेस नहीं है। "
                    "सटीकता बनाए रखने के लिए, नगरवॉच कोई काल्पनिक डेटा नहीं बनाता। कृपया अपने रेसिडेंट डैशबोर्ड में स्थिति देखें।"
                )
            elif lang == LanguageDetection.HINGLISH:
                answer = (
                    "Mere paas abhi aapke live report records ya incident database ka access nahi hai. "
                    "Accuracy maintain karne ke liye, NagarWatch koi fabricated status provide nahi karta. Kripya apne resident dashboard me check karein."
                )
            else:
                answer = (
                    "I do not currently have access to live incident records or specific report status in the database. "
                    "To ensure data integrity, NagarWatch never invents report details. Please check your resident dashboard for live tracking."
                )

            return AssistantResponse(
                answer=answer,
                detected_language=lang,
                confidence=0.90,
                requires_database_data=True,
                source="local_fallback",
                limitations=["Live database context is unavailable; no incident records were generated or assumed."],
                evaluated_at=datetime.now(timezone.utc),
            )

        # 3. How to report an incident
        if any(k in q_lower for k in ["how to report", "submit report", "file a complaint", "kaise report", "report kaise kare", "शिकायत कैसे दर्ज करें", "रिपोर्ट कैसे"]):
            if lang == LanguageDetection.HINDI:
                answer = (
                    "नगरवॉच पर समस्या रिपोर्ट करने के लिए: 1. 'Report Incident' पर क्लिक करें। "
                    "2. समस्या का स्पष्ट विवरण दें। 3. सही श्रेणी (सड़क, स्वच्छता, आदि) चुनें। "
                    "4. सटीक स्थान या लैंडमार्क दर्ज करें। 5. सुरक्षित होने पर एक फोटो संलग्न करें और सबमिट करें।"
                )
            elif lang == LanguageDetection.HINGLISH:
                answer = (
                    "NagarWatch par incident report karne ke liye: 1. 'Report Incident' par click karein. "
                    "2. Problem ka clear description likhein. 3. Sahi category select karein. "
                    "4. Exact location ya landmark verify karein. 5. Safe ho to photo attach karein aur submit karein."
                )
            else:
                answer = (
                    "To report an incident on NagarWatch: 1. Click 'Report Incident'. "
                    "2. Describe the civic hazard clearly. 3. Select the appropriate category (Infrastructure, Sanitation, Traffic, etc.). "
                    "4. Confirm the location coordinates or landmark. 5. Attach a clear photo if safe to do so, then submit."
                )

            return AssistantResponse(
                answer=answer,
                detected_language=lang,
                confidence=0.95,
                requires_database_data=False,
                source="local_fallback",
                limitations=[],
                evaluated_at=datetime.now(timezone.utc),
            )

        # 4. Priority levels explanation
        if any(k in q_lower for k in ["priority", "critical priority", "high priority", "priority levels", "प्राथमिकता"]):
            if lang == LanguageDetection.HINDI:
                answer = (
                    "नगरवॉच प्राथमिकता (0-100 स्केल) 4 घटकों पर तय करता है: गंभीरता (40%), सत्यापन (25%), नवीनता (20%) और प्रभावित क्षेत्र (15%)। "
                    "श्रेणियां हैं: Critical (75-100, जानलेवा खतरे), High (50-74), Moderate (30-49), और Low (0-29)। गंभीर खतरों को तुरंत समीक्षा के लिए भेजा जाता है।"
                )
            elif lang == LanguageDetection.HINGLISH:
                answer = (
                    "NagarWatch priority (0-100 scale) 4 components par calculate hoti hai: Severity (40%), Community Verification (25%), "
                    "Recency (20%), aur Affected Area (15%). Priority bands: Critical (75-100, urgent hazards), High (50-74), Moderate (30-49), "
                    "aur Low (0-29). Serious safety threats hamesha immediate human review ke liye escalate hote hain."
                )
            else:
                answer = (
                    "NagarWatch calculates priority (0-100 scale) using Severity (40%), Community Verification (25%), Recency (20%), "
                    "and Affected Area (15%). Bands are: Critical (75-100, immediate life-safety hazards), High (50-74), Moderate (30-49), "
                    "and Low (0-29). Serious safety hazards are always escalated for immediate human review regardless of vote count."
                )

            return AssistantResponse(
                answer=answer,
                detected_language=lang,
                confidence=0.95,
                requires_database_data=False,
                source="local_fallback",
                limitations=[],
                evaluated_at=datetime.now(timezone.utc),
            )

        # 5. Status meanings
        if any(k in q_lower for k in ["status mean", "under review", "in progress", "resolved", "pending triage", "स्टेटस"]):
            if lang == LanguageDetection.HINDI:
                answer = (
                    "नगरवॉच रिपोर्ट के चरण: 1. Submitted/Pending Triage: रिपोर्ट प्राप्त हुई। "
                    "2. Under Review: सुरक्षा दल द्वारा मूल्यांकन जारी है। 3. In Progress: संबंधित अधिकारियों या रखरखाव दल को भेजा गया। "
                    "4. Resolved: समस्या का समाधान हो चुका है। 5. Closed: मामला औपचारिक रूप से बंद हुआ।"
                )
            elif lang == LanguageDetection.HINGLISH:
                answer = (
                    "NagarWatch report statuses: 1. Submitted/Pending Triage: Report receive ho chuki hai. "
                    "2. Under Review: Safety dispatchers evaluate kar rahe hain. 3. In Progress: Municipal/maintenance team ko assign ho gayi hai. "
                    "4. Resolved: Hazard solve ho gaya hai. 5. Closed: Case successfully close ho gaya."
                )
            else:
                answer = (
                    "NagarWatch report lifecycle statuses: 1. 'Submitted/Pending Triage': Received and queued for assessment. "
                    "2. 'Under Review': Being evaluated by human dispatchers. 3. 'In Progress': Assigned to local maintenance or civic authorities. "
                    "4. 'Resolved': Hazard has been verified fixed. 5. 'Closed': Issue concluded with final notes."
                )

            return AssistantResponse(
                answer=answer,
                detected_language=lang,
                confidence=0.95,
                requires_database_data=False,
                source="local_fallback",
                limitations=[],
                evaluated_at=datetime.now(timezone.utc),
            )

        # 6. Off-topic / Unrelated query handling
        off_topic_indicators = [
            "weather", "movie", "recipe", "cricket", "joke", "code", "python", "capital of",
            "गाना", "मौसम", "फिल्म", "क्रिकेट"
        ]
        if any(k in q_lower for k in off_topic_indicators):
            if lang == LanguageDetection.HINDI:
                answer = "मैं नगरवॉच सामुदायिक सुरक्षा सहायक हूँ, जो नागरिक सुरक्षा और समस्याओं की रिपोर्टिंग में सहायता करता है। मैं असंबंधित विषयों में सहायता नहीं कर सकता।"
            elif lang == LanguageDetection.HINGLISH:
                answer = "Main NagarWatch Community Assistant hoon, jo local community safety aur civic hazards report karne me madad karta hai. Main unrelated topics par assist nahi kar sakta."
            else:
                answer = "I am the NagarWatch Community Assistant, dedicated to hyperlocal civic safety and incident reporting. I cannot assist with unrelated general queries. How can I help you with civic safety today?"

            return AssistantResponse(
                answer=answer,
                detected_language=lang,
                confidence=0.85,
                requires_database_data=False,
                source="local_fallback",
                limitations=["Query is outside the scope of NagarWatch civic safety platform."],
                evaluated_at=datetime.now(timezone.utc),
            )

        # 7. Default general platform guidance
        if lang == LanguageDetection.HINDI:
            answer = "नगरवॉच एक सामुदायिक सुरक्षा नेटवर्क है जहाँ नागरिक खुले मैनहोल, टूटी स्ट्रीट लाइट, गड्ढे और कचरे जैसी समस्याओं की रिपोर्ट और निगरानी कर सकते हैं।"
        elif lang == LanguageDetection.HINGLISH:
            answer = "NagarWatch ek hyperlocal community safety platform hai jahan residents civic issues jaise broken streetlights, potholes, open manholes aur garbage report aur track kar sakte hain."
        else:
            answer = "NagarWatch is a hyperlocal community safety network helping residents report, verify, and resolve neighborhood hazards like broken streetlights, potholes, and sanitation issues."

        return AssistantResponse(
            answer=answer,
            detected_language=lang,
            confidence=0.85,
            requires_database_data=False,
            source="local_fallback",
            limitations=[],
            evaluated_at=datetime.now(timezone.utc),
        )


def ask_community_assistant(
    query: str,
    context: Optional[Dict[str, Any]] = None,
    client: Optional[Any] = None,
    config: Optional[GeminiClientConfig] = None,
    fallback_enabled: bool = True,
) -> AssistantResponse:
    """Convenience function to ask the community assistant."""
    assistant = CommunityAssistant(client=client, config=config, fallback_enabled=fallback_enabled)
    return assistant.ask(query=query, context=context)
