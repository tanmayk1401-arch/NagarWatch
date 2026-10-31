from django.urls import path
from . import views

urlpatterns = [
    # Authentication
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),

    # Resident pages
    path("", views.resident_dashboard, name="resident_dashboard"),
    path("report/", views.report_issue, name="report_issue"),
    path("explore/", views.explore_issues, name="explore_issues"),
    path("issue/<int:report_id>/", views.issue_detail, name="issue_detail"),
    path(
        "issue/<int:report_id>/feedback/",
        views.incident_feedback,
        name="incident_feedback"
    ),
    path("map/", views.map_view, name="map_view"),
    path("my-reports/", views.my_reports, name="my_reports"),
    path("notifications/", views.notifications, name="notifications"),
    path(
        "notifications/mark-read/",
        views.mark_notifications_read,
        name="mark_notifications_read"
    ),

    # Admin pages
    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-moderation/", views.admin_moderation, name="admin_moderation"),
    path(
        "admin-moderation/<int:report_id>/",
        views.moderate_incident,
        name="moderate_incident"
    ),

    # AI Assistants
    path("api/assistant/community/", views.api_community_assistant, name="api_community_assistant"),
    path("api/assistant/admin/", views.api_admin_assistant, name="api_admin_assistant"),
]
