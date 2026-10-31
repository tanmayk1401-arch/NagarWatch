from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (AIAnalysis, Department, DuplicateCandidate, Issue, IssuePhoto,
                     IssueVerification, ModerationNote, Notification, User)

admin.site.register(User, UserAdmin)
for model in (Issue, Department, ModerationNote, IssuePhoto, IssueVerification,
              DuplicateCandidate, AIAnalysis, Notification):
    admin.site.register(model)