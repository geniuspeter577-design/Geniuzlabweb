from django.contrib import admin
from .models import (
    Skill, CreativeProfile, PortfolioItem, ProjectMedia, ProjectLike,
    ProjectComment, ProjectShare, SavedProject, ProjectReport, Follow,
    ServiceRequest, Job, JobApplication, CollaborationRequest, SavedCreative, Review,
)

admin.site.register(Skill)


class ProjectMediaInline(admin.TabularInline):
    model = ProjectMedia
    extra = 0


@admin.register(PortfolioItem)
class PortfolioItemAdmin(admin.ModelAdmin):
    list_display = ("title", "creative", "category", "views_count", "is_reported_hidden", "created_at")
    list_filter = ("category", "is_reported_hidden")
    search_fields = ("title", "description", "creative__user__username")
    inlines = [ProjectMediaInline]


@admin.register(ProjectReport)
class ProjectReportAdmin(admin.ModelAdmin):
    list_display = ("project", "reporter", "reason", "created_at")
    list_filter = ("reason",)


@admin.register(ProjectComment)
class ProjectCommentAdmin(admin.ModelAdmin):
    list_display = ("project", "user", "created_at")


@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("follower", "following", "created_at")


admin.site.register(ProjectLike)
admin.site.register(ProjectShare)
admin.site.register(SavedProject)


class PortfolioInline(admin.TabularInline):
    model = PortfolioItem
    extra = 0


@admin.register(CreativeProfile)
class CreativeProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "experience_years", "is_available")
    list_filter = ("category", "is_available")
    inlines = [PortfolioInline]


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("client", "creative", "status", "created_at")
    list_filter = ("status",)


class JobApplicationInline(admin.TabularInline):
    model = JobApplication
    extra = 0


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ("title", "poster", "category", "status", "created_at")
    list_filter = ("category", "status")
    inlines = [JobApplicationInline]


@admin.register(CollaborationRequest)
class CollaborationRequestAdmin(admin.ModelAdmin):
    list_display = ("from_user", "to_user", "status", "created_at")
    list_filter = ("status",)


@admin.register(SavedCreative)
class SavedCreativeAdmin(admin.ModelAdmin):
    list_display = ("customer", "creative", "created_at")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("reviewer", "creative", "rating", "created_at")
    list_filter = ("rating",)
