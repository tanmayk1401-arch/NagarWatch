from django.urls import path
from django.views.generic import RedirectView

from . import views

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="login", permanent=False)),
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("dashboard/", views.resident_dashboard, name="resident_dashboard"),
    path("issues/", views.explore_issues, name="explore_issues"),
    path("issues/<int:report_id>/", views.issue_detail, name="issue_detail"),
    path("map/", views.map_view, name="map_view"),
    path("my-reports/", views.my_reports, name="my_reports"),
    path("notifications/", views.notifications, name="notifications"),
    path("report/", views.report_issue, name="report_issue"),
    path("admin-panel/", views.admin_dashboard, name="admin_dashboard"),
    path("admin-panel/moderation/", views.admin_moderation, name="admin_moderation"),
]