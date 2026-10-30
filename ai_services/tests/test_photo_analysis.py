"""Unit tests for NagarWatch Photo Analysis Service.

Verifies:
1. Successful vision analysis returning complete structured results.
2. Safety hazard detection and category relevance assessment.
3. Policy constraints:
   - Never claims proof of authenticity, date, location, or cause.
   - Never recommends automated rejection of resident reports.
4. Input validation and error handling:
   - Missing images (None, empty bytes).
   - Unsupported image formats.
   - Oversized images (>10MB limit).
   - Non-existent file paths.
5. Upstream Gemini API error handling:
   - Timeouts and 504 Deadline Exceeded -> GeminiTimeoutError.
   - General API errors -> GeminiAPIError.
   - Empty or unparseable model responses -> ClassificationValidationError.
6. Input flexibility: Raw bytes, file-like objects (io.BytesIO), and file paths.
"""

import io
import json
from unittest.mock import MagicMock
import pytest

from ai_services.exceptions import (
    ClassificationValidationError,
    GeminiAPIError,
    GeminiTimeoutError,
)
from ai_services.photo_analysis import (
    PhotoAnalysisResult,
    PhotoAnalyzer,
    analyze_photo,
)

# Sample valid image byte signatures for testing
VALID_JPEG_BYTES = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\x00" * 64
VALID_PNG_BYTES = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" + b"\x00" * 64


def create_mock_vision_client(response_text: str):
    """Helper creating a mocked Gen AI client returning the specified response text."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = response_text
    mock_client.models.generate_content.return_value = mock_response
    return mock_client


# ==============================================================================
# Successful Photo Analysis Tests
# ==============================================================================

def test_successful_photo_analysis_complete_payload():
    """Verify photo analysis returns a fully validated PhotoAnalysisResult."""
    mock_payload = {
        "visible_description": "An open circular manhole on an asphalt roadway without safety cones or barricades.",
        "safety_hazards": ["Open hole hazard", "Trip and fall risk for pedestrians", "Vehicle tire damage"],
        "is_relevant_to_claim": True,
        "confidence": 0.94,
        "limitations": ["Shadow obscuring internal depth of the manhole", "No visible street signage in frame"],
        "explanation": "The photograph clearly shows an uncovered utility manhole in the traffic lane, directly supporting the claimed Infrastructure issue."
    }
    client = create_mock_vision_client(json.dumps(mock_payload))
    analyzer = PhotoAnalyzer(client=client)

    result = analyzer.analyze_photo(
        image=VALID_JPEG_BYTES,
        incident_description="Open manhole near market entrance, dangerous at night",
        claimed_category="Infrastructure",
    )

    assert isinstance(result, PhotoAnalysisResult)
    assert "open circular manhole" in result.visible_description
    assert len(result.safety_hazards) == 3
    assert "Open hole hazard" in result.safety_hazards
    assert result.is_relevant_to_claim is True
    assert result.confidence == 0.94
    assert len(result.limitations) == 2
    assert "uncovered utility manhole" in result.explanation
    assert result.rejection_recommended is False
    assert "does not prove or verify" in result.authenticity_disclaimer.lower()
    assert result.evaluated_at is not None


def test_markdown_code_fence_cleaning():
    """Verify that model output wrapped in markdown code blocks is stripped and parsed."""
    wrapped_json = """```json
    {
        "visible_description": "Overflowing public dumpster with scattered plastic bags on the sidewalk.",
        "safety_hazards": ["Biological waste exposure", "Sidewalk pedestrian obstruction"],
        "is_relevant_to_claim": true,
        "confidence": 0.89,
        "limitations": ["Photo taken at dusk with moderate graininess"],
        "explanation": "Visible garbage accumulation aligns with the reported sanitation concern."
    }
    ```"""
    client = create_mock_vision_client(wrapped_json)
    analyzer = PhotoAnalyzer(client=client)

    result = analyzer.analyze_photo(image=VALID_PNG_BYTES)
    assert result.is_relevant_to_claim is True
    assert result.confidence == 0.89
    assert "Overflowing public dumpster" in result.visible_description


def test_photo_analysis_irrelevant_image():
    """Verify analysis when image content is not relevant to claimed incident."""
    mock_payload = {
        "visible_description": "A well-lit indoor living room with a sofa and television.",
        "safety_hazards": [],
        "is_relevant_to_claim": False,
        "confidence": 0.92,
        "limitations": ["Indoor setting cannot confirm outdoor conditions"],
        "explanation": "The image shows an indoor living space which does not appear visually relevant to a reported sewer overflow."
    }
    client = create_mock_vision_client(json.dumps(mock_payload))
    analyzer = PhotoAnalyzer(client=client)

    result = analyzer.analyze_photo(
        image=VALID_JPEG_BYTES,
        incident_description="Sewage overflow on 4th cross road",
        claimed_category="Sanitation & Health",
    )

    assert result.is_relevant_to_claim is False
    # Even if irrelevant, automated rejection is prohibited
    assert result.rejection_recommended is False
    assert "does not prove" in result.authenticity_disclaimer.lower()


# ==============================================================================
# Policy & Non-Rejection Verification Tests
# ==============================================================================

def test_policy_no_authenticity_claim_and_never_auto_reject():
    """Enforces policy: Never claim definitive proof; never auto-reject reports."""
    mock_payload = {
        "visible_description": "Damaged asphalt surface.",
        "safety_hazards": ["Road surface irregularity"],
        "is_relevant_to_claim": None,
        "confidence": 0.65,
        "limitations": ["Close-up angle without surrounding landmarks"],
        "explanation": "Visible asphalt damage is consistent with road degradation, but location cannot be established."
    }
    client = create_mock_vision_client(json.dumps(mock_payload))
    result = analyze_photo(
        image=VALID_JPEG_BYTES,
        client=client,
    )

    assert result.rejection_recommended is False
    assert "does not prove or verify" in result.authenticity_disclaimer.lower()
    assert "authenticity" in result.authenticity_disclaimer.lower()
    assert "date" in result.authenticity_disclaimer.lower()
    assert "location" in result.authenticity_disclaimer.lower()
    assert "cause" in result.authenticity_disclaimer.lower()


# ==============================================================================
# Input Validation & Unsupported Format Tests
# ==============================================================================

def test_missing_image_raises_value_error():
    """Missing or None image input must raise ValueError."""
    analyzer = PhotoAnalyzer(client=MagicMock())

    with pytest.raises(ValueError, match="Image must be provided"):
        analyzer.analyze_photo(image=None)

    with pytest.raises(ValueError, match="Image data is empty"):
        analyzer.analyze_photo(image=b"")


def test_unsupported_image_format_raises_value_error():
    """Unrecognized or unsupported image byte headers must raise ValueError."""
    analyzer = PhotoAnalyzer(client=MagicMock())
    invalid_data = b"PLAIN_TEXT_NOT_AN_IMAGE_FILE_CONTENT"

    with pytest.raises(ValueError, match="Unsupported or unidentifiable image format"):
        analyzer.analyze_photo(image=invalid_data)


def test_oversized_image_raises_value_error():
    """Images exceeding the maximum allowable size (10MB) must raise ValueError."""
    analyzer = PhotoAnalyzer(client=MagicMock())
    # 10MB + 1 byte
    oversized_data = b"\xff\xd8\xff" + (b"\x00" * (10 * 1024 * 1024 + 1))

    with pytest.raises(ValueError, match="exceeds maximum allowable limit"):
        analyzer.analyze_photo(image=oversized_data)


def test_nonexistent_file_path_raises_file_not_found():
    """Non-existent file paths must raise FileNotFoundError."""
    analyzer = PhotoAnalyzer(client=MagicMock())

    with pytest.raises(FileNotFoundError, match="Image file does not exist"):
        analyzer.analyze_photo(image="non_existent_image_12345.jpg")


# ==============================================================================
# Flexible Input Types: File Paths and File-Like Objects
# ==============================================================================

def test_file_path_input(tmp_path):
    """Verify analyzing image from a valid on-disk file path."""
    test_img = tmp_path / "incident_photo.jpg"
    test_img.write_bytes(VALID_JPEG_BYTES)

    mock_payload = {
        "visible_description": "Road surface with visible fracture lines.",
        "safety_hazards": ["Road fracture"],
        "is_relevant_to_claim": True,
        "confidence": 0.85,
        "limitations": ["Limited illumination"],
        "explanation": "Visible crack aligns with road maintenance issue."
    }
    client = create_mock_vision_client(json.dumps(mock_payload))
    analyzer = PhotoAnalyzer(client=client)

    result = analyzer.analyze_photo(image=str(test_img))
    assert result.confidence == 0.85
    assert "Road surface with visible fracture" in result.visible_description


def test_file_like_object_input():
    """Verify analyzing image from an in-memory BytesIO object."""
    file_obj = io.BytesIO(VALID_PNG_BYTES)

    mock_payload = {
        "visible_description": "Broken streetlight fixture dangling from a utility pole.",
        "safety_hazards": ["Falling object hazard", "Exposed wiring"],
        "is_relevant_to_claim": True,
        "confidence": 0.91,
        "limitations": ["No night view to assess darkness"],
        "explanation": "Fixture damage visually corroborates reported streetlight malfunction."
    }
    client = create_mock_vision_client(json.dumps(mock_payload))
    analyzer = PhotoAnalyzer(client=client)

    result = analyzer.analyze_photo(image=file_obj)
    assert result.confidence == 0.91
    assert "Broken streetlight fixture" in result.visible_description


# ==============================================================================
# Upstream Error Handling & Malformed Response Tests
# ==============================================================================

def test_api_timeout_raises_gemini_timeout_error():
    """Network or API timeouts must raise GeminiTimeoutError."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = TimeoutError("Deadline exceeded after 30000ms")
    analyzer = PhotoAnalyzer(client=mock_client)

    with pytest.raises(GeminiTimeoutError, match="timed out"):
        analyzer.analyze_photo(image=VALID_JPEG_BYTES)


def test_deadline_exceeded_raises_gemini_timeout_error():
    """504 Gateway Timeout or Deadline Exceeded must raise GeminiTimeoutError."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("504 Gateway Timeout: Deadline Exceeded")
    analyzer = PhotoAnalyzer(client=mock_client)

    with pytest.raises(GeminiTimeoutError, match="timed out"):
        analyzer.analyze_photo(image=VALID_JPEG_BYTES)


def test_upstream_api_failure_raises_gemini_api_error():
    """Upstream API or quota failures must raise GeminiAPIError."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("429 Resource has been exhausted")
    analyzer = PhotoAnalyzer(client=mock_client)

    with pytest.raises(GeminiAPIError, match="Google Gemini API error"):
        analyzer.analyze_photo(image=VALID_JPEG_BYTES)


def test_empty_model_response_raises_validation_error():
    """Empty or null model responses must raise ClassificationValidationError."""
    client = create_mock_vision_client("   ")
    analyzer = PhotoAnalyzer(client=client)

    with pytest.raises(ClassificationValidationError, match="empty or null"):
        analyzer.analyze_photo(image=VALID_JPEG_BYTES)


def test_malformed_json_response_raises_validation_error():
    """Unparseable model outputs must raise ClassificationValidationError."""
    client = create_mock_vision_client("I cannot analyze this image right now.")
    analyzer = PhotoAnalyzer(client=client)

    with pytest.raises(ClassificationValidationError, match="schema validation"):
        analyzer.analyze_photo(image=VALID_JPEG_BYTES)


def test_invalid_schema_confidence_out_of_range():
    """Model responses with out-of-range confidence scores must fail validation."""
    invalid_payload = {
        "visible_description": "Valid description.",
        "safety_hazards": [],
        "is_relevant_to_claim": True,
        "confidence": 1.75,  # Out of range!
        "limitations": [],
        "explanation": "Valid explanation."
    }
    client = create_mock_vision_client(json.dumps(invalid_payload))
    analyzer = PhotoAnalyzer(client=client)

    with pytest.raises(ClassificationValidationError):
        analyzer.analyze_photo(image=VALID_JPEG_BYTES)


def test_to_dict_serialization():
    """Verify result dictionary serialization."""
    mock_payload = {
        "visible_description": "Smoke visible rising from open plot.",
        "safety_hazards": ["Smoke inhalation", "Potential fire spread"],
        "is_relevant_to_claim": True,
        "confidence": 0.88,
        "limitations": ["Distance obscures the fire source"],
        "explanation": "Visible smoke corroborates reported burning."
    }
    client = create_mock_vision_client(json.dumps(mock_payload))
    result = analyze_photo(image=VALID_JPEG_BYTES, client=client)
    data = result.to_dict()

    assert isinstance(data, dict)
    assert data["visible_description"] == mock_payload["visible_description"]
    assert data["confidence"] == 0.88
    assert data["rejection_recommended"] is False
    assert "evaluated_at" in data
    assert "authenticity_disclaimer" in data
