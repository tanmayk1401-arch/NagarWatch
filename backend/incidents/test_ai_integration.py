"""Comprehensive test suite for NagarWatch AI-to-Django integration.

Covers:
1. Incident classification in issue submission.
2. Category & severity mapping to Issue model choices.
3. Priority scoring (0.40S + 0.25V + 0.20R + 0.15A) with verification feedback.
4. Duplicate incident candidate detection & human review policy (no auto-merge/delete).
5. Photo analysis integration & non-blocking error handling.
6. Authenticated community assistant endpoint & emergency intercept.
7. Admin-protected admin assistant endpoint & factual statistics.
8. Fallback behavior when Gemini is unavailable.
"""

import io
from unittest.mock import MagicMock, patch
from PIL import Image

from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from incidents.models import (
    Issue,
    IssuePhoto,
    IssueVerification,
    DuplicateCandidate,
    AIAnalysis,
    User,
)
from incidents.ai_integration import (
    map_ai_category_to_choice,
    map_severity_to_choice,
    map_priority_band_to_choice,
    compute_priority_inputs,
    process_issue_ai_pipeline,
    process_issue_photos,
    evaluate_issue_duplicates,
)
from ai_services.schemas import IncidentCategory, IncidentSeverity, IncidentClassificationResult
from ai_services.priority_service import PriorityBand, PriorityAssessment
from ai_services.photo_analysis import PhotoAnalysisResult
from ai_services.exceptions import GeminiTimeoutError, GeminiAPIError
from ai_services.classification import IncidentClassifier


class CategoryAndSeverityMappingTests(TestCase):
    """Verify safe mapping between AI taxonomy and Django model choices."""

    def test_map_ai_category_to_choice(self):
        valid_choices = dict(Issue.CATEGORY_CHOICES)

        self.assertIn(map_ai_category_to_choice(IncidentCategory.TRAFFIC_ROAD_HAZARD), valid_choices)
        self.assertEqual(map_ai_category_to_choice(IncidentCategory.TRAFFIC_ROAD_HAZARD), "Roads & Footpaths")

        self.assertIn(map_ai_category_to_choice(IncidentCategory.SANITATION_HEALTH), valid_choices)
        self.assertEqual(map_ai_category_to_choice(IncidentCategory.SANITATION_HEALTH), "Garbage & Waste")

        self.assertEqual(
            map_ai_category_to_choice(IncidentCategory.INFRASTRUCTURE, subcategory="Streetlight", text="dark pole"),
            "Streetlights",
        )
        self.assertEqual(
            map_ai_category_to_choice(IncidentCategory.INFRASTRUCTURE, subcategory="Drainage", text="water leakage"),
            "Water & Drainage",
        )
        self.assertEqual(
            map_ai_category_to_choice(IncidentCategory.INFRASTRUCTURE, subcategory="Roads", text="deep pothole"),
            "Roads & Footpaths",
        )
        self.assertEqual(
            map_ai_category_to_choice(IncidentCategory.INFRASTRUCTURE, subcategory="Parks", text="broken bench in park"),
            "Parks & Public Spaces",
        )

        self.assertIn(map_ai_category_to_choice(IncidentCategory.FIRE_ENVIRONMENTAL), valid_choices)
        self.assertIn(map_ai_category_to_choice(IncidentCategory.NOISE_DISTURBANCE), valid_choices)
        self.assertIn(map_ai_category_to_choice(IncidentCategory.OTHER), valid_choices)

    def test_map_severity_to_choice(self):
        valid_priorities = dict(Issue.PRIORITY_CHOICES)

        self.assertEqual(map_severity_to_choice(IncidentSeverity.LOW), "low")
        self.assertEqual(map_severity_to_choice(IncidentSeverity.MEDIUM), "medium")
        self.assertEqual(map_severity_to_choice(IncidentSeverity.HIGH), "high")
        self.assertEqual(map_severity_to_choice(IncidentSeverity.CRITICAL), "urgent")

        for sev in IncidentSeverity:
            self.assertIn(map_severity_to_choice(sev), valid_priorities)

    def test_map_priority_band_to_choice(self):
        valid_priorities = dict(Issue.PRIORITY_CHOICES)

        self.assertEqual(map_priority_band_to_choice(PriorityBand.LOW), "low")
        self.assertEqual(map_priority_band_to_choice(PriorityBand.MODERATE), "medium")
        self.assertEqual(map_priority_band_to_choice(PriorityBand.HIGH), "high")
        self.assertEqual(map_priority_band_to_choice(PriorityBand.CRITICAL), "urgent")


class IssueSubmissionAndAIPipelineTests(TestCase):
    """Test AI triage pipeline integration on issue creation."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="citizen1",
            email="citizen1@example.com",
            password="testpassword123",
            role=User.Role.CITIZEN,
        )
        self.client = Client()
        self.client.login(username="citizen1", password="testpassword123")

    @patch.object(IncidentClassifier, "classify_incident")
    def test_issue_submission_executes_ai_pipeline(self, mock_classify):
        """Verify issue creation triggers classification, priority, and saves AIAnalysis."""
        mock_classify.return_value = IncidentClassificationResult(
            original_description="Dangerous deep pothole on main road causing accidents daily.",
            category=IncidentCategory.TRAFFIC_ROAD_HAZARD,
            subcategory="Pothole / Road damage",
            severity=IncidentSeverity.HIGH,
            language="English",
            confidence=0.96,
            explanation="Pothole poses immediate vehicle hazard.",
            source="gemini",
            model_name="gemini-2.5-flash",
        )
        post_data = {
            "title": "Severe road pothole causing bike skidding",
            "description": "Dangerous deep pothole on main road causing accidents daily.",
            "category": "Roads & Footpaths",
            "location": "MG Road, Ward 4",
            "latitude": "12.9716",
            "longitude": "77.5946",
        }

        response = self.client.post(reverse("report_issue"), post_data, follow=True)
        self.assertEqual(response.status_code, 200)

        issue = Issue.objects.get(title="Severe road pothole causing bike skidding")
        # Ensure resident original input is preserved
        self.assertEqual(issue.description, post_data["description"])
        self.assertEqual(issue.category, post_data["category"])

        # Ensure AI fields are populated
        self.assertTrue(bool(issue.ai_category))
        self.assertGreaterEqual(issue.ai_confidence, 0)
        self.assertIn(issue.ai_severity, dict(Issue.PRIORITY_CHOICES))
        self.assertIsNotNone(issue.priority_score)
        self.assertGreaterEqual(issue.priority_score, 0.0)
        self.assertLessEqual(issue.priority_score, 100.0)

        # Check AIAnalysis records
        classification_analysis = AIAnalysis.objects.filter(
            issue=issue, service_name=AIAnalysis.ServiceName.CLASSIFICATION
        )
        self.assertTrue(classification_analysis.exists())

        priority_analysis = AIAnalysis.objects.filter(
            issue=issue, service_name=AIAnalysis.ServiceName.PRIORITY
        )
        self.assertTrue(priority_analysis.exists())

        # Check documented unresolved inputs in metadata
        self.assertIn("unresolved_inputs", issue.ai_metadata)
        self.assertIn("verification_formula", issue.ai_metadata["unresolved_inputs"])
        self.assertIn("recency_formula", issue.ai_metadata["unresolved_inputs"])
        self.assertIn("affected_area_formula", issue.ai_metadata["unresolved_inputs"])

    def test_priority_score_updates_on_community_verification(self):
        """Verify that voting confirm/dispute recalculates the priority score."""
        issue = Issue.objects.create(
            title="Dark street at night",
            description="All lights on street broken",
            category="Streetlights",
            reported_by=self.user,
            priority_score=40.0,
            priority="medium",
            ai_severity="medium",
        )
        initial_score = issue.priority_score

        # Citizen submits confirm feedback
        resp = self.client.post(
            reverse("incident_feedback", args=[issue.pk]),
            {"action": "confirm"},
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)

        issue.refresh_from_db()
        self.assertEqual(issue.upvotes, 1)
        # Net vote increased, so priority score should increase
        self.assertGreater(issue.priority_score, initial_score)

    def test_fallback_when_gemini_fails_during_intake(self):
        """Verify deterministic fallback runs gracefully when remote Gemini times out."""
        with patch("ai_services.classification.get_gemini_client") as mock_client:
            mock_client.side_effect = GeminiTimeoutError("Deadline exceeded.")

            issue = Issue.objects.create(
                title="Pothole in street",
                description="Sadak par bohot bada gaddha hai paani bhara hai",
                category="Roads & Footpaths",
                reported_by=self.user,
            )

            # Run pipeline under mock failure
            process_issue_ai_pipeline(issue)
            issue.refresh_from_db()

            # Classification should succeed via local fallback
            self.assertEqual(issue.ai_category, "Roads & Footpaths")
            analysis = AIAnalysis.objects.filter(
                issue=issue, service_name=AIAnalysis.ServiceName.CLASSIFICATION
            ).first()
            self.assertIsNotNone(analysis)
            self.assertEqual(analysis.source, AIAnalysis.Source.FALLBACK)


class DuplicateDetectionIntegrationTests(TestCase):
    """Test duplicate detection integration, candidate recording, and non-rejection policy."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="citizendup",
            email="dup@example.com",
            password="testpassword123",
        )

    def test_duplicate_candidates_saved_for_human_review(self):
        """Verify possible duplicates create DuplicateCandidate records and never auto-delete."""
        # Existing issue
        existing = Issue.objects.create(
            title="Major Pothole on 5th Cross Road",
            description="Deep crater 2 feet wide on 5th Cross road near pharmacy",
            category="Roads & Footpaths",
            status="pending",
            reported_by=self.user,
            latitude=12.9716,
            longitude=77.5946,
        )

        # New issue almost identical in text, location, category
        new_issue = Issue.objects.create(
            title="Dangerous pothole on 5th Cross",
            description="Deep crater 2 feet wide on 5th Cross road near pharmacy",
            category="Roads & Footpaths",
            status="pending",
            reported_by=self.user,
            latitude=12.9716,
            longitude=77.5946,
        )

        candidates = evaluate_issue_duplicates(new_issue)
        new_issue.refresh_from_db()

        # Should create a DuplicateCandidate
        self.assertGreaterEqual(len(candidates), 1)
        candidate_rec = DuplicateCandidate.objects.get(
            issue=new_issue, candidate_issue=existing
        )
        self.assertGreaterEqual(candidate_rec.similarity_score, 60.0)
        self.assertEqual(candidate_rec.review_status, DuplicateCandidate.ReviewStatus.PENDING)

        # Strong duplicate sets ai_is_duplicate flag
        if candidate_rec.similarity_score >= 80.0:
            self.assertTrue(new_issue.ai_is_duplicate)
            self.assertEqual(new_issue.ai_duplicate_of, existing)

        # STRICT POLICY: Original issue is NOT rejected, merged, or deleted
        self.assertEqual(new_issue.status, "pending")
        self.assertTrue(Issue.objects.filter(pk=new_issue.pk).exists())
        self.assertTrue(Issue.objects.filter(pk=existing.pk).exists())


class PhotoAnalysisIntegrationTests(TestCase):
    """Test photo analysis integration and error resiliency."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="citizenphoto",
            email="photo@example.com",
            password="testpassword123",
        )
        # Create a small valid image in memory
        img = Image.new("RGB", (64, 64), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="JPEG")
        self.uploaded_photo = SimpleUploadedFile(
            "pothole.jpg", img_bytes.getvalue(), content_type="image/jpeg"
        )

    def test_photo_analysis_populates_issue_photo_fields(self):
        issue = Issue.objects.create(
            title="Pothole photo test",
            description="Pothole picture",
            category="Roads & Footpaths",
            reported_by=self.user,
        )
        photo = IssuePhoto.objects.create(
            issue=issue,
            image=self.uploaded_photo,
            uploaded_by=self.user,
        )

        mock_result = PhotoAnalysisResult(
            visible_description="Visible deep asphalt depression on road surface.",
            safety_hazards=["Skidding hazard"],
            is_relevant_to_claim=True,
            confidence=0.92,
            limitations=["Limited daylight"],
            explanation="Image displays clear road damage consistent with a pothole.",
        )

        mock_analyzer = MagicMock()
        mock_analyzer.analyze_photo.return_value = mock_result
        mock_analyzer.model_name = "gemini-2.5-flash"

        process_issue_photos(issue, analyzer=mock_analyzer)

        photo.refresh_from_db()
        self.assertEqual(photo.ai_description, mock_result.visible_description)
        self.assertAlmostEqual(photo.ai_confidence, 0.92)
        self.assertIn("visible_description", photo.ai_metadata)

        # Verify AIAnalysis record created
        analysis = AIAnalysis.objects.filter(
            issue=issue, service_name=AIAnalysis.ServiceName.PHOTO
        ).first()
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.source, AIAnalysis.Source.GEMINI)

    def test_photo_analysis_failure_does_not_crash(self):
        """Verify photo analysis failure gracefully writes fallback without crashing."""
        issue = Issue.objects.create(
            title="Photo error test",
            description="Broken light",
            category="Streetlights",
            reported_by=self.user,
        )
        photo = IssuePhoto.objects.create(
            issue=issue,
            image=self.uploaded_photo,
            uploaded_by=self.user,
        )

        mock_analyzer = MagicMock()
        mock_analyzer.analyze_photo.side_effect = GeminiAPIError("Vision quota exceeded.")

        # Should not raise exception
        results = process_issue_photos(issue, analyzer=mock_analyzer)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "fallback")

        photo.refresh_from_db()
        self.assertTrue(len(photo.ai_description) > 0)


class AssistantEndpointsTests(TestCase):
    """Test Community Assistant and Admin Assistant HTTP endpoints."""

    def setUp(self):
        self.citizen = User.objects.create_user(
            username="citizentest",
            email="citizentest@example.com",
            password="testpassword123",
            role=User.Role.CITIZEN,
        )
        self.admin = User.objects.create_user(
            username="admintest",
            email="admintest@example.com",
            password="testpassword123",
            role=User.Role.ADMIN,
        )
        self.issue = Issue.objects.create(
            title="Broken drainage pipe",
            description="Water overflowing on sidewalk",
            category="Water & Drainage",
            status="pending",
            priority="urgent",
            reported_by=self.citizen,
        )

    def test_community_assistant_requires_authentication(self):
        client = Client()
        resp = client.post(
            reverse("api_community_assistant"),
            {"query": "How do I report an issue?"},
        )
        # Should redirect to login
        self.assertEqual(resp.status_code, 302)

    @patch("ai_services.community_assistant.get_gemini_client")
    def test_community_assistant_authenticated_response(self, mock_client):
        mock_client.side_effect = GeminiTimeoutError("Mock timeout")
        client = Client()
        client.login(username="citizentest", password="testpassword123")

        resp = client.post(
            reverse("api_community_assistant"),
            data='{"query": "How does priority work in NagarWatch?"}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("answer", data)
        self.assertIn("detected_language", data)

    def test_community_assistant_emergency_intercept(self):
        client = Client()
        client.login(username="citizentest", password="testpassword123")

        resp = client.post(
            reverse("api_community_assistant"),
            data='{"query": "Building on fire right now call emergency help!"}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        # Must intercept and instruct 112 / emergency dispatch
        self.assertIn("112", data["answer"])

    def test_admin_assistant_denied_for_citizen(self):
        client = Client()
        client.login(username="citizentest", password="testpassword123")

        resp = client.post(
            reverse("api_admin_assistant"),
            data='{"query": "Show summary of all complaints"}',
            content_type="application/json",
        )
        # Citizen should be redirected / denied
        self.assertEqual(resp.status_code, 302)

    @patch("ai_services.admin_assistant.get_gemini_client")
    def test_admin_assistant_authorized_for_admin(self, mock_client):
        mock_client.side_effect = GeminiTimeoutError("Mock timeout")
        client = Client()
        client.login(username="admintest", password="testpassword123")

        resp = client.post(
            reverse("api_admin_assistant"),
            data='{"query": "Summarize total issues and category distribution"}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("answer", data)
        self.assertIn("statistics_used", data)
        self.assertIn("total_incidents", data["statistics_used"])
