
import json
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.views.decorators.http import require_http_methods, require_POST
from django.db import transaction
from django.db.models import Q, Count, Case, When, IntegerField
from django.core.paginator import Paginator

from .models import (
    Issue,
    IssuePhoto,
    IssueVerification,
    Department,
    ModerationNote,
    Notification,
    DuplicateCandidate,
    AIAnalysis,
)


from .ai_integration import (
    process_issue_ai_pipeline,
    process_issue_photos,
    compute_priority_inputs,
    map_priority_band_to_choice,
    handle_community_assistant_query,
    handle_admin_assistant_query,
)
from ai_services.priority_service import PriorityService


User = get_user_model()
PAGE_SIZE = 9

PRIORITY_ORDER = Case(
    When(priority="urgent", then=1),
    When(priority="high", then=2),
    When(priority="medium", then=3),
    When(priority="low", then=4),
    output_field=IntegerField(),
)


# ==========================================================
# ACCESS CONTROL
# ==========================================================

def is_admin(user):
    return (
        user.is_authenticated
        and (
            user.is_superuser
            or user.is_staff
            or user.role == "ADMIN"
        )
    )


def admin_required(view_func):
    return user_passes_test(
        is_admin,
        login_url="login"
    )(view_func)


# ==========================================================
# AUTHENTICATION
# ==========================================================

@require_http_methods(["GET", "POST"])
def login_view(request):

    if request.user.is_authenticated:
        return redirect(
            "admin_dashboard" if is_admin(request.user)
            else "resident_dashboard"
        )

    if request.method == "POST":

        identifier = (
            request.POST.get("identifier")
            or request.POST.get("email_or_username")
            or request.POST.get("username")
            or request.POST.get("email")
            or ""
        ).strip()

        password = request.POST.get("password", "")

        user_record = User.objects.filter(
            Q(username__iexact=identifier)
            | Q(email__iexact=identifier)
        ).first()

        username = user_record.username if user_record else identifier

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)

            next_url = request.GET.get("next") or request.POST.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)

            return redirect(
                "admin_dashboard" if is_admin(user)
                else "resident_dashboard"
            )

        messages.error(request, "Invalid email/username or password.")

    return render(request, "auth/login.html")


@require_http_methods(["GET", "POST"])
def register_view(request):

    if request.user.is_authenticated:
        return redirect("resident_dashboard")

    if request.method == "POST":

        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if not all([full_name, email, password, confirm_password]):
            messages.error(request, "Please complete all fields.")

        elif password != confirm_password:
            messages.error(request, "Passwords do not match.")

        elif User.objects.filter(email__iexact=email).exists():
            messages.error(request, "This email is already registered.")

        else:
            first_name = full_name.split()[0]
            last_name = " ".join(full_name.split()[1:])

            User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role="CITIZEN",
            )

            messages.success(
                request,
                "Registration successful. Please log in."
            )
            return redirect("login")

    return render(request, "auth/register.html")


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("login")


# ==========================================================
# RESIDENT DASHBOARD
# ==========================================================

@login_required
def resident_dashboard(request):

    reports = Issue.objects.filter(
        reported_by=request.user
    )

    context = {
        "active_page": "dashboard",
        "total_reports": reports.count(),
        "pending_reports": reports.filter(status="pending").count(),
        "verified_reports": reports.filter(status="verified").count(),
        "in_progress_reports": reports.filter(
            status="in_progress"
        ).count(),
        "resolved_reports": reports.filter(status="resolved").count(),
        "recent_reports": reports[:4],
    }

    return render(request, "resident/dashboard.html", context)


# ==========================================================
# REPORT AN ISSUE
# ==========================================================

@login_required
@require_http_methods(["GET", "POST"])
def report_issue(request):

    if request.method == "POST":

        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        category = request.POST.get("category", "").strip()

        latitude = request.POST.get("latitude") or None
        longitude = request.POST.get("longitude") or None

        location = request.POST.get("location", "").strip()
        occurred_at = request.POST.get("occurred_at") or None

        valid_categories = dict(Issue.CATEGORY_CHOICES)

        if not title or not category:
            messages.error(request, "Title and category are required.")

        elif category not in valid_categories:
            messages.error(request, "Please select a valid category.")

        else:
            try:
                with transaction.atomic():

                    issue = Issue.objects.create(
                        title=title,
                        description=description,
                        category=category,
                        reported_by=request.user,
                        latitude=latitude,
                        longitude=longitude,
                        location=location,
                        occurred_at=occurred_at,
                    )

                    photos = request.FILES.getlist("photos")

                    # Also accept a single-photo input named "photo".
                    if not photos and request.FILES.get("photo"):
                        photos = [request.FILES["photo"]]

                    for uploaded_image in photos:
                        IssuePhoto.objects.create(
                            issue=issue,
                            image=uploaded_image,
                            uploaded_by=request.user,
                        )

                    Notification.objects.create(
                        user=request.user,
                        issue=issue,
                        title="Report submitted",
                        message=f"Your report '{issue.title}' was submitted successfully.",
                    )

                # Execute AI triage pipeline (classification, priority, duplicate detection)
                process_issue_ai_pipeline(issue)

                # Execute photo analysis for any uploaded photos
                if photos:
                    process_issue_photos(issue)

                messages.success(
                    request,
                    "Your issue has been submitted successfully."
                )

                return redirect("issue_detail", report_id=issue.pk)

            except (ValueError, TypeError):
                messages.error(
                    request,
                    "Please check the location and date values."
                )

    return render(
        request,
        "resident/report_issue.html",
        {"active_page": "report"}
    )


# ==========================================================
# EXPLORE ISSUES
# ==========================================================

@login_required
def explore_issues(request):

    issues = Issue.objects.all()

    search = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    status = request.GET.get("status", "").strip()
    priority = request.GET.get("priority", "").strip()
    sort = request.GET.get("sort", "newest")

    if search:
        issues = issues.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(location__icontains=search)
            | Q(id_code__icontains=search)
        )

    if category in dict(Issue.CATEGORY_CHOICES):
        issues = issues.filter(category=category)

    if status in dict(Issue.STATUS_CHOICES):
        issues = issues.filter(status=status)

    if priority in dict(Issue.PRIORITY_CHOICES):
        issues = issues.filter(priority=priority)

    if sort == "oldest":
        issues = issues.order_by("created_at")

    elif sort == "priority":
        issues = issues.order_by(PRIORITY_ORDER, "-created_at")

    else:
        issues = issues.order_by("-created_at")

    page_obj = Paginator(issues, PAGE_SIZE).get_page(
        request.GET.get("page")
    )

    context = {
        "active_page": "explore",
        "incidents": page_obj,
        "issues": page_obj,
        "page_obj": page_obj,
        "search": search,
        "selected_category": category,
        "selected_status": status,
        "selected_priority": priority,
        "selected_sort": sort,
        "categories": Issue.CATEGORY_CHOICES,
        "statuses": Issue.STATUS_CHOICES,
        "priorities": Issue.PRIORITY_CHOICES,
    }

    return render(request, "resident/explore_issues.html", context)


# ==========================================================
# ISSUE DETAILS
# ==========================================================

@login_required
def issue_detail(request, report_id):

    issue = get_object_or_404(
        Issue.objects.prefetch_related("photos", "verifications", "duplicate_candidates__candidate_issue"),
        pk=report_id
    )

    context = {
        "active_page": "explore",
        "incident": issue,
        "issue": issue,
        "photos": issue.photos.all(),
        "confirm_count": issue.upvotes,
        "dispute_count": issue.disputes,
        "user_vote": IssueVerification.objects.filter(
            issue=issue,
            user=request.user
        ).first(),
        "ai_analyses": issue.ai_analyses.all(),
        "duplicate_candidates": issue.duplicate_candidates.select_related("candidate_issue").all(),
    }

    return render(request, "resident/issue_detail.html", context)


# ==========================================================
# COMMUNITY CONFIRM / DISPUTE
# ==========================================================

@login_required
@require_POST
def incident_feedback(request, report_id):

    issue = get_object_or_404(Issue, pk=report_id)

    action = request.POST.get("action", "").lower()

    if action not in ["confirm", "dispute"]:
        messages.error(request, "Invalid feedback.")
        return redirect("issue_detail", report_id=report_id)

    with transaction.atomic():

        vote, created = IssueVerification.objects.update_or_create(
            issue=issue,
            user=request.user,
            defaults={"vote": action}
        )

        issue.upvotes = issue.verifications.filter(
            vote="confirm"
        ).count()

        issue.disputes = issue.verifications.filter(
            vote="dispute"
        ).count()

        # Recalculate priority score with updated verification data
        s, v, r, a, _ = compute_priority_inputs(issue)
        p_res = PriorityService.calculate(
            severity=s,
            verification=v,
            recency=r,
            affected_area=a,
            immediate_safety_hazard=(issue.ai_severity == "urgent"),
        )
        issue.priority_score = p_res.score
        issue.priority = map_priority_band_to_choice(p_res.band)
        issue.save(update_fields=["upvotes", "disputes", "priority_score", "priority"])

    messages.success(request, "Your feedback has been recorded.")

    return redirect("issue_detail", report_id=report_id)


# ==========================================================
# MAP VIEW
# ==========================================================

@login_required
def map_view(request):

    issues = Issue.objects.exclude(
        latitude__isnull=True
    ).exclude(
        longitude__isnull=True
    )

    category = request.GET.get("category")
    status = request.GET.get("status")

    if category in dict(Issue.CATEGORY_CHOICES):
        issues = issues.filter(category=category)

    if status in dict(Issue.STATUS_CHOICES):
        issues = issues.filter(status=status)

    context = {
        "active_page": "map",
        "incidents": issues,
        "issues": issues,
        "incident_count": issues.count(),
        "carto_api_key": getattr(settings, "CARTO_API_KEY", "YOUR_CARTO_API_KEY"),
    }

    return render(request, "resident/map_view.html", context)


# ==========================================================
# MY REPORTS
# ==========================================================

@login_required
def my_reports(request):

    reports = Issue.objects.filter(
        reported_by=request.user
    )

    status = request.GET.get("status", "").strip()

    if status in dict(Issue.STATUS_CHOICES):
        reports = reports.filter(status=status)

    page_obj = Paginator(reports, PAGE_SIZE).get_page(
        request.GET.get("page")
    )

    context = {
        "active_page": "my_reports",
        "reports": page_obj,
        "issues": page_obj,
        "page_obj": page_obj,
        "selected_status": status,
    }

    return render(request, "resident/my_reports.html", context)


# ==========================================================
# NOTIFICATIONS
# ==========================================================

@login_required
def notifications(request):

    user_notifications = Notification.objects.filter(
        user=request.user
    )

    context = {
        "active_page": "notifications",
        "notifications": user_notifications,
        "unread_count": user_notifications.filter(
            is_read=False
        ).count(),
    }

    return render(request, "resident/notifications.html", context)


@login_required
@require_POST
def mark_notifications_read(request):

    Notification.objects.filter(
        user=request.user,
        is_read=False
    ).update(is_read=True)

    messages.success(request, "Notifications marked as read.")

    return redirect("notifications")


# ==========================================================
# ADMIN DASHBOARD
# ==========================================================

@login_required
@admin_required
def admin_dashboard(request):

    issues = Issue.objects.all()

    category_stats = (
        issues.values("category")
        .annotate(total=Count("id"))
        .order_by("-total")
    )

    context = {
        "is_admin": True,
        "total_incidents": issues.count(),
        "pending_incidents": issues.filter(status="pending").count(),
        "verified_incidents": issues.filter(status="verified").count(),
        "in_progress_incidents": issues.filter(
            status="in_progress"
        ).count(),
        "resolved_incidents": issues.filter(status="resolved").count(),
        "rejected_incidents": issues.filter(status="rejected").count(),
        "recent_incidents": issues[:6],
        "category_stats": category_stats,
    }

    return render(request, "admin/dashboard.html", context)


# ==========================================================
# ADMIN MODERATION QUEUE
# ==========================================================

@login_required
@admin_required
def admin_moderation(request):

    issues = Issue.objects.select_related(
        "reported_by",
        "assigned_department"
    ).all()

    search = request.GET.get("q", "").strip()
    status = request.GET.get("status", "").strip()
    category = request.GET.get("category", "").strip()

    if search:
        issues = issues.filter(
            Q(title__icontains=search)
            | Q(description__icontains=search)
            | Q(id_code__icontains=search)
        )

    if status in dict(Issue.STATUS_CHOICES):
        issues = issues.filter(status=status)

    if category in dict(Issue.CATEGORY_CHOICES):
        issues = issues.filter(category=category)

    page_obj = Paginator(issues, PAGE_SIZE).get_page(
        request.GET.get("page")
    )

    context = {
        "is_admin": True,
        "incidents": page_obj,
        "issues": page_obj,
        "page_obj": page_obj,
        "departments": Department.objects.all(),
        "categories": Issue.CATEGORY_CHOICES,
        "statuses": Issue.STATUS_CHOICES,
    }

    return render(request, "admin/moderation.html", context)


# ==========================================================
# ADMIN MODERATION ACTIONS
# ==========================================================

@login_required
@admin_required
@require_POST
def moderate_incident(request, report_id):

    issue = get_object_or_404(Issue, pk=report_id)

    action = request.POST.get("action", "").lower()

    status_actions = {
        "verify": "verified",
        "in_progress": "in_progress",
        "resolve": "resolved",
        "reject": "rejected",
    }

    if action in status_actions:

        issue.status = status_actions[action]

        if action == "verify":
            issue.progress_stage = "ward_assignment"
            issue.progress_percentage = max(
                issue.progress_percentage, 20
            )

        elif action == "in_progress":
            issue.progress_stage = "crew_dispatch"
            issue.progress_percentage = max(
                issue.progress_percentage, 60
            )

        elif action == "resolve":
            issue.progress_stage = "closed"
            issue.progress_percentage = 100

        issue.save()

        messages.success(request, "Issue status updated.")

    elif action == "duplicate":

        issue.ai_is_duplicate = True
        issue.save(update_fields=["ai_is_duplicate"])

        messages.info(
            request,
            "Issue flagged as a possible duplicate for review."
        )

    elif action == "assign_department":

        department_id = request.POST.get("department_id")

        department = get_object_or_404(
            Department,
            pk=department_id
        )

        issue.assigned_department = department
        issue.save(update_fields=["assigned_department"])

        messages.success(request, "Department assigned.")

    elif action == "add_note":

        note_text = request.POST.get("note", "").strip()

        if note_text:
            ModerationNote.objects.create(
                issue=issue,
                author=request.user,
                text=note_text
            )
            messages.success(request, "Moderation note added.")
        else:
            messages.error(request, "Note cannot be empty.")

    else:
        messages.error(request, "Unknown moderation action.")

    return redirect("admin_moderation")


# ==========================================================
# AI ASSISTANT API ENDPOINTS
# ==========================================================

@login_required
@require_POST
def api_community_assistant(request):
    """Authenticated endpoint for resident multilingual safety assistant."""
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except (ValueError, UnicodeDecodeError):
        data = request.POST

    query = (data.get("query") or "").strip()
    issue_id = data.get("issue_id")

    if not query:
        return JsonResponse({"error": "Query cannot be empty."}, status=400)

    try:
        issue_id_int = int(issue_id) if issue_id else None
    except (ValueError, TypeError):
        issue_id_int = None

    try:
        result = handle_community_assistant_query(
            query=query,
            user=request.user,
            issue_id=issue_id_int,
        )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": "Assistant service unavailable.", "detail": str(e)}, status=500)


@login_required
@admin_required
@require_POST
def api_admin_assistant(request):
    """Admin-protected endpoint for administrative intelligence queries."""
    try:
        data = json.loads(request.body.decode("utf-8")) if request.body else {}
    except (ValueError, UnicodeDecodeError):
        data = request.POST

    query = (data.get("query") or "").strip()

    if not query:
        return JsonResponse({"error": "Query cannot be empty."}, status=400)

    try:
        result = handle_admin_assistant_query(
            query=query,
            user=request.user,
        )
        return JsonResponse(result)
    except Exception as e:
        return JsonResponse({"error": "Admin assistant unavailable.", "detail": str(e)}, status=500)
