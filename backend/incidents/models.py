"""
NagarWatch models - MERGED version.

Base: Member 2's Issue model (the frontend templates and mock data depend on
its field names, integer ids and lowercase choices).
Added from Member 3's schema: custom User role, priority_score, occurred_at,
ai_metadata, IssueVerification, DuplicateCandidate, AIAnalysis and photo AI fields.

Refinements in this version:
  - User.email is unique (the login page says "Email or Username")
  - Issue.assigned_department (moderation page "assign department" dropdown)
  - Notification model (the app has a Notifications page)

Left open on purpose (not decided by the team yet):
  - how V, R and A are computed for the priority score
  - mapping between the classifier's categories and CATEGORY_CHOICES below
  - public comments (Member 3's IncidentComment): the frontend has none, so skipped
"""

from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.urls import reverse
from django.utils import timezone


class User(AbstractUser):
    """Single user system with a role. Do not create a second user model."""

    class Role(models.TextChoices):
        CITIZEN = "CITIZEN", "Citizen"
        ADMIN = "ADMIN", "Admin"

    email = models.EmailField("email address", unique=True)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.CITIZEN)


def issue_image_upload_path(instance, filename):
    # instance.id does not exist yet when a photo is first saved, so use the date only
    return f"issues/{timezone.now():%Y/%m/%d}/{filename}"


class Issue(models.Model):
    """Civic issue reported by a resident or identified by an admin."""

    CATEGORY_CHOICES = [
        ("Roads & Footpaths", "Roads & Footpaths"),
        ("Streetlights", "Streetlights & Electricity"),
        ("Water & Drainage", "Water Supply & Drainage"),
        ("Garbage & Waste", "Garbage & Waste Management"),
        ("Parks & Public Spaces", "Parks & Public Spaces"),
        ("Other", "Other Community Infrastructure"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending Review"),
        ("verified", "Verified"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("rejected", "Rejected / Spam"),
    ]
    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]
    PROGRESS_CHOICES = [
        ("field_verification", "Stage 1: Field Verification"),
        ("ward_assignment", "Stage 2: Ward Assignment"),
        ("crew_dispatch", "Stage 3: Crew Dispatch"),
        ("resolution", "Stage 4: Resolution"),
        ("closed", "Stage 5: Closed"),
    ]

    # Identification. Integer pk (frontend URLs use whole numbers, e.g. 101).
    id_code = models.CharField(
        max_length=10, unique=True, null=True, blank=True,
        help_text="e.g. NW-101, filled automatically on first save",
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)  # resident's original text, never overwritten by AI

    # Categorization, status, priority
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, default="Roads & Footpaths"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")
    # Raw 0-100 score from the AI priority service (the band maps onto `priority`)
    priority_score = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # Location and time
    latitude = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    location = models.CharField(max_length=255, blank=True)
    ward = models.CharField(max_length=50, blank=True)
    occurred_at = models.DateTimeField(
        null=True, blank=True, help_text="When the problem happened (used for recency)"
    )

    # Assigned by an admin on the moderation page
    assigned_department = models.ForeignKey(
        "Department", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="issues",
    )

    # Ownership and timestamps
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="reported_issues",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Moderation / AI fields (suggestions only, a human decides)
    ai_category = models.CharField(max_length=50, blank=True)
    ai_confidence = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    ai_severity = models.CharField(
        max_length=20, blank=True, choices=PRIORITY_CHOICES, default="medium"
    )
    ai_is_duplicate = models.BooleanField(default=False)
    ai_duplicate_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="duplicates_of",
    )
    ai_metadata = models.JSONField(default=dict, blank=True)

    # Community verification (cached counts, details are in IssueVerification)
    upvotes = models.IntegerField(default=0)
    disputes = models.IntegerField(default=0)

    # UI progress bar
    progress_stage = models.CharField(
        max_length=30, blank=True, choices=PROGRESS_CHOICES, default="field_verification"
    )
    progress_percentage = models.IntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Civic Issue"
        verbose_name_plural = "Civic Issues"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["category"]),
            models.Index(fields=["priority"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["latitude", "longitude"]),
        ]

    def __str__(self):
        return f"{self.id_code or self.pk} - {self.title}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.id_code:
            self.id_code = f"NW-{self.pk}"
            super().save(update_fields=["id_code"])

    def get_absolute_url(self):
        return reverse("issue_detail", args=[self.pk])

    # Helpers used by the templates
    def get_status_badge_class(self):
        mapping = {
            "pending": "badge-warning",
            "verified": "badge-primary",
            "in_progress": "badge-info",
            "resolved": "badge-success",
            "rejected": "badge-danger",
        }
        return mapping.get(self.status, "badge-neutral")

    def get_priority_badge_class(self):
        mapping = {
            "low": "badge-success",
            "medium": "badge-neutral",
            "high": "badge-warning",
            "urgent": "badge-danger",
        }
        return mapping.get(self.priority, "badge-neutral")

    def get_progress_color(self):
        mapping = {
            "field_verification": "progress-pending",
            "ward_assignment": "progress-warning",
            "crew_dispatch": "progress-in-progress",
            "resolution": "progress-resolved",
            "closed": "progress-resolved",
        }
        return mapping.get(self.progress_stage, "progress-pending")


class Department(models.Model):
    """Used by the admin moderation 'assign department' dropdown."""

    name = models.CharField(max_length=100, unique=True)
    abbreviation = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name


class ModerationNote(models.Model):
    """Internal notes and dispatch instructions."""

    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="notes")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note on {self.issue_id}"


class IssuePhoto(models.Model):
    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to=issue_image_upload_path)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    # Advisory photo-analysis output (Member 3)
    ai_description = models.TextField(blank=True)
    ai_confidence = models.FloatField(
        null=True, blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
    )
    ai_metadata = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"Photo for {self.issue_id}"


class IssueVerification(models.Model):
    """One community vote per user per issue."""

    class Vote(models.TextChoices):
        CONFIRM = "confirm", "Confirm"
        DISPUTE = "dispute", "Dispute"

    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="verifications")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="verifications"
    )
    vote = models.CharField(max_length=20, choices=Vote.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["issue", "user"], name="one_vote_per_user_per_issue"
            )
        ]

    def __str__(self):
        return f"{self.user_id} {self.vote} {self.issue_id}"


class DuplicateCandidate(models.Model):
    """Advisory only. Never merge, delete or reject reports automatically."""

    class ReviewStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        REJECTED = "REJECTED", "Rejected"

    issue = models.ForeignKey(
        Issue, on_delete=models.CASCADE, related_name="duplicate_candidates"
    )
    candidate_issue = models.ForeignKey(
        Issue, on_delete=models.CASCADE, related_name="possible_duplicate_of"
    )
    similarity_score = models.FloatField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    review_status = models.CharField(
        max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING
    )
    evaluated_at = models.DateTimeField(default=timezone.now)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="reviewed_duplicates",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["issue", "candidate_issue"], name="unique_duplicate_pair"
            ),
            models.CheckConstraint(
                condition=~Q(issue=F("candidate_issue")),
                name="duplicate_issues_must_differ",
            ),
        ]

    def __str__(self):
        return f"{self.issue_id} ~ {self.candidate_issue_id} ({self.similarity_score})"


class AIAnalysis(models.Model):
    """Stored output of the AI services, kept apart from the resident's own text."""

    class ServiceName(models.TextChoices):
        CLASSIFICATION = "CLASSIFICATION", "Classification"
        PRIORITY = "PRIORITY", "Priority"
        DUPLICATE = "DUPLICATE", "Duplicate"
        PHOTO = "PHOTO", "Photo"
        COMMUNITY = "COMMUNITY", "Community"
        ADMIN = "ADMIN", "Admin"

    class Source(models.TextChoices):
        GEMINI = "GEMINI", "Gemini"
        FALLBACK = "FALLBACK", "Fallback"
        RULE_BASED = "RULE_BASED", "Rule based"

    issue = models.ForeignKey(Issue, on_delete=models.CASCADE, related_name="ai_analyses")
    service_name = models.CharField(max_length=50, choices=ServiceName.choices)
    result = models.JSONField(default=dict)
    confidence = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=30, choices=Source.choices)
    model_name = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name_plural = "AI analyses"

    def __str__(self):
        return f"{self.service_name} for {self.issue_id}"


class Notification(models.Model):
    """Shown on the Notifications page. Types and wording are still to be agreed."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications"
    )
    issue = models.ForeignKey(
        Issue, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications"
    )
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} -> {self.user_id}"
