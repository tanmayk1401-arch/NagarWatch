"""NagarWatch AI Services package.

Standalone AI and intelligence layer for hyperlocal community safety.
Provides multilingual incident triage, structured validation, and Gemini API orchestration.
"""

from ai_services.admin_assistant import (
    AdminAssistant,
    AdminAssistantResponse,
    ask_admin_assistant,
)
from ai_services.classification import IncidentClassifier
from ai_services.exceptions import (
    AIServiceError,
    ClassificationValidationError,
    GeminiAPIError,
    GeminiConfigurationError,
    GeminiTimeoutError,
)
from ai_services.gemini_client import GeminiClientConfig, get_gemini_client
from ai_services.community_assistant import (
    AssistantResponse,
    CommunityAssistant,
    ask_community_assistant,
)
from ai_services.duplicate_service import (
    DuplicateAssessment,
    DuplicateDecision,
    DuplicateService,
    detect_duplicates,
)
from ai_services.photo_analysis import (
    PhotoAnalysisResult,
    PhotoAnalyzer,
    analyze_photo,
)
from ai_services.priority_service import (
    PriorityAssessment,
    PriorityBand,
    PriorityService,
    calculate_priority,
)
from ai_services.schemas import (
    IncidentCategory,
    IncidentClassificationResult,
    IncidentSeverity,
    LanguageDetection,
)

__all__ = [
    "IncidentClassifier",
    "IncidentClassificationResult",
    "IncidentCategory",
    "IncidentSeverity",
    "LanguageDetection",
    "GeminiClientConfig",
    "get_gemini_client",
    "AIServiceError",
    "GeminiConfigurationError",
    "GeminiAPIError",
    "GeminiTimeoutError",
    "ClassificationValidationError",
    "PriorityService",
    "PriorityAssessment",
    "PriorityBand",
    "calculate_priority",
    "DuplicateService",
    "DuplicateAssessment",
    "DuplicateDecision",
    "detect_duplicates",
    "PhotoAnalyzer",
    "PhotoAnalysisResult",
    "analyze_photo",
    "CommunityAssistant",
    "AssistantResponse",
    "ask_community_assistant",
    "AdminAssistant",
    "AdminAssistantResponse",
    "ask_admin_assistant",
]
