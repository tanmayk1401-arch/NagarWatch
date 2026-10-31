from django.shortcuts import render


# Temporary views: they only show Member 2's pages.
# Real data, login and permissions are added later.

def login_view(request):
    return render(request, "auth/login.html")


def register_view(request):
    return render(request, "auth/register.html")


def resident_dashboard(request):
    return render(request, "resident/dashboard.html", {"active_page": "dashboard"})


def explore_issues(request):
    return render(request, "resident/explore_issues.html", {"active_page": "explore"})


def issue_detail(request, report_id):
    return render(request, "resident/issue_detail.html",
                  {"active_page": "explore", "report_id": report_id})


def map_view(request):
    return render(request, "resident/map_view.html", {"active_page": "map"})


def my_reports(request):
    return render(request, "resident/my_reports.html", {"active_page": "my_reports"})


def notifications(request):
    return render(request, "resident/notifications.html", {"active_page": "notifications"})


def report_issue(request):
    return render(request, "resident/report_issue.html", {"active_page": "report"})


def admin_dashboard(request):
    return render(request, "admin/dashboard.html", {"is_admin": True})


def admin_moderation(request):
    return render(request, "admin/moderation.html", {"is_admin": True})