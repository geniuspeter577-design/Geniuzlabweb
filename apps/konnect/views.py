from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import models
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from geniuzlab.validators import validate_image_upload, validate_project_media
from apps.notifications.utils import notify
from .models import (
    CreativeProfile, PortfolioItem, ProjectMedia, ProjectLike, ProjectComment,
    ProjectShare, SavedProject, ProjectReport, Follow, PROJECT_CATEGORY_CHOICES,
    ServiceRequest, Job, JobApplication, CollaborationRequest, Skill,
    SavedCreative, Review,
)


def _visible_projects():
    """Base queryset for anything shown publicly (feed, discover, search,
    homepage) — excludes projects hidden after a moderation review."""
    return PortfolioItem.objects.filter(is_reported_hidden=False).select_related(
        "creative__user"
    ).prefetch_related("media")


def hire_creative(request):
    """Browse creatives — the public marketplace listing."""
    creatives = CreativeProfile.objects.filter(is_available=True).select_related("user")

    category = request.GET.get("category")
    if category:
        creatives = creatives.filter(category=category)

    query = request.GET.get("q")
    if query:
        creatives = creatives.filter(headline__icontains=query)

    return render(request, "pages/hire_creative.html", {
        "creatives": creatives,
        "categories": CreativeProfile.CATEGORY_CHOICES,
        "selected_category": category or "",
        "query": query or "",
    })


def creative_detail(request, pk):
    creative = get_object_or_404(CreativeProfile, pk=pk)
    if not request.user.is_authenticated or request.user != creative.user:
        CreativeProfile.objects.filter(pk=pk).update(profile_views=models.F("profile_views") + 1)
        creative.refresh_from_db(fields=["profile_views"])

    is_saved = False
    is_following = False
    if request.user.is_authenticated:
        is_saved = SavedCreative.objects.filter(customer=request.user, creative=creative).exists()
        from .models import Follow
        is_following = Follow.objects.filter(follower=request.user, following=creative.user).exists()

    return render(request, "konnect/creative_detail.html", {
        "creative": creative,
        "is_saved": is_saved,
        "is_following": is_following,
        "reviews": creative.reviews.select_related("reviewer")[:10],
    })


@login_required
def create_creative_profile(request):
    profile, _ = CreativeProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile.headline = request.POST.get("headline", "")
        profile.category = request.POST.get("category", "other")
        profile.bio = request.POST.get("bio", "")
        profile.experience_years = request.POST.get("experience_years") or 0
        profile.hourly_rate = request.POST.get("hourly_rate") or None
        profile.location = request.POST.get("location", "")
        profile.services_offered = request.POST.get("services_offered", "")
        profile.website_url = request.POST.get("website_url", "")
        profile.instagram_url = request.POST.get("instagram_url", "")
        profile.twitter_url = request.POST.get("twitter_url", "")
        profile.linkedin_url = request.POST.get("linkedin_url", "")
        if request.FILES.get("avatar"):
            avatar_file = request.FILES["avatar"]
            try:
                validate_image_upload(avatar_file)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
                return redirect("edit_creative_profile")
            profile.avatar = avatar_file
        profile.save()

        skills_raw = request.POST.get("skills", "")
        skill_names = [s.strip() for s in skills_raw.split(",") if s.strip()]
        skill_objs = []
        for name in skill_names:
            skill, _ = Skill.objects.get_or_create(name__iexact=name, defaults={"name": name})
            skill_objs.append(skill)
        profile.skills.set(skill_objs)

        promoted = False
        if request.user.role == "customer":
            request.user.role = "creative"
            request.user.save(update_fields=["role"])
            promoted = True

        if promoted:
            messages.success(
                request,
                "Your creative profile is live \u2014 your dashboard has switched to Creative mode.",
            )
        else:
            messages.success(request, "Your creative profile has been saved.")
        return redirect("dashboard")

    return render(request, "konnect/edit_creative_profile.html", {"profile": profile})


def _media_type_for(upload_file):
    name = (upload_file.name or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    return "video" if ext in {"mp4", "mov", "webm", "m4v"} else "image"


@login_required
def portfolio_dashboard(request):
    """The Creative Portfolio Dashboard: list/manage all of the creative's
    own projects (upload, edit, delete)."""
    profile = get_object_or_404(CreativeProfile, user=request.user)
    items = profile.portfolio_items.all()
    return render(request, "konnect/portfolio_dashboard.html", {
        "profile": profile,
        "items": items,
        "categories": PROJECT_CATEGORY_CHOICES,
    })


@login_required
def add_portfolio_item(request):
    profile = get_object_or_404(CreativeProfile, user=request.user)

    if request.method == "POST":
        image_file = request.FILES.get("image")
        if image_file:
            try:
                validate_image_upload(image_file)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
                return redirect("add_portfolio_item")

        project = PortfolioItem.objects.create(
            creative=profile,
            title=request.POST.get("title", ""),
            description=request.POST.get("description", ""),
            category=request.POST.get("category", "other"),
            link=request.POST.get("link", ""),
            image=image_file,
        )

        gallery_files = request.FILES.getlist("gallery")
        errors = []
        for order, upload_file in enumerate(gallery_files):
            try:
                validate_project_media(upload_file)
            except ValidationError as exc:
                errors.append(f"{upload_file.name}: {'; '.join(exc.messages)}")
                continue
            ProjectMedia.objects.create(
                project=project, file=upload_file,
                media_type=_media_type_for(upload_file), order=order,
            )
        if errors:
            messages.warning(request, "Some files were skipped — " + " | ".join(errors))

        project.save()  # backfills cover image from gallery if none was set
        messages.success(request, "Project uploaded — it's now live in the Home Feed.")
        return redirect("project_detail", pk=project.pk)

    return render(request, "konnect/add_portfolio_item.html", {"categories": PROJECT_CATEGORY_CHOICES})


@login_required
def edit_portfolio_item(request, pk):
    project = get_object_or_404(PortfolioItem, pk=pk, creative__user=request.user)

    if request.method == "POST":
        project.title = request.POST.get("title", project.title)
        project.description = request.POST.get("description", project.description)
        project.category = request.POST.get("category", project.category)
        project.link = request.POST.get("link", "")

        image_file = request.FILES.get("image")
        if image_file:
            try:
                validate_image_upload(image_file)
                project.image = image_file
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
                return redirect("edit_portfolio_item", pk=pk)

        project.save()

        gallery_files = request.FILES.getlist("gallery")
        if gallery_files:
            start_order = project.media.count()
            for offset, upload_file in enumerate(gallery_files):
                try:
                    validate_project_media(upload_file)
                except ValidationError as exc:
                    messages.warning(request, f"{upload_file.name}: {'; '.join(exc.messages)}")
                    continue
                ProjectMedia.objects.create(
                    project=project, file=upload_file,
                    media_type=_media_type_for(upload_file), order=start_order + offset,
                )

        remove_media_ids = request.POST.getlist("remove_media")
        if remove_media_ids:
            project.media.filter(pk__in=remove_media_ids).delete()

        messages.success(request, "Project updated.")
        return redirect("project_detail", pk=project.pk)

    return render(request, "konnect/edit_portfolio_item.html", {
        "project": project, "categories": PROJECT_CATEGORY_CHOICES,
    })


@login_required
@require_POST
def delete_portfolio_item(request, pk):
    project = get_object_or_404(PortfolioItem, pk=pk, creative__user=request.user)
    project.delete()
    messages.success(request, "Project deleted.")
    return redirect("portfolio_dashboard")


@login_required
def request_service(request, pk):
    creative = get_object_or_404(CreativeProfile, pk=pk)

    if request.method == "POST":
        conversation = None
        if request.user.is_authenticated and creative.user != request.user:
            from apps.chat.models import Conversation

            conversation = (
                Conversation.objects.filter(participants=request.user)
                .filter(participants=creative.user)
                .first()
            )
            if not conversation:
                conversation = Conversation.objects.create()
                conversation.participants.add(request.user, creative.user)

        ServiceRequest.objects.create(
            client=request.user,
            creative=creative,
            message=request.POST.get("message", ""),
            budget=request.POST.get("budget") or None,
            conversation=conversation,
        )
        notify(creative.user, f"{request.user.username} requested your services.", link="/service-requests/", category="client_request")
        messages.success(request, "Your request has been sent to the creative.")
        return redirect("creative_detail", pk=pk)

    return render(request, "konnect/request_service.html", {"creative": creative})


@login_required
def my_service_requests(request):
    sent = request.user.service_requests_sent.all()
    received = ServiceRequest.objects.filter(creative__user=request.user)
    return render(request, "konnect/service_requests.html", {"sent": sent, "received": received})


@login_required
@require_POST
def respond_service_request(request, pk, action):
    """Lets the creative accept/decline a hire request — previously the
    ServiceRequest.status field had no path to ever leave 'pending'."""
    service_request = get_object_or_404(ServiceRequest, pk=pk, creative__user=request.user)
    if action == "accept":
        service_request.status = "accepted"
        notify(
            service_request.client,
            f"{request.user.username} accepted your service request.",
            link="/service-requests/", category="client_request",
        )
        messages.success(request, "Request accepted.")
    elif action == "decline":
        service_request.status = "declined"
        notify(
            service_request.client,
            f"{request.user.username} declined your service request.",
            link="/service-requests/", category="client_request",
        )
        messages.info(request, "Request declined.")
    service_request.save(update_fields=["status"])
    return redirect("my_service_requests")


def jobs(request):
    # select_related the poster (avoids a query per card if the template
    # ever needs it) and annotate applicant_count so the list page runs one
    # query total instead of one extra COUNT per job (job.applicant_count()
    # is auto-called by the template for every card in the loop). The
    # annotation shadows the Job.applicant_count() model method by name for
    # these instances, which is safe: nothing calls it explicitly elsewhere.
    job_list = Job.objects.filter(status="open").select_related("poster").annotate(
        applicant_count=Count("applications")
    )
    category = request.GET.get("category")
    if category:
        job_list = job_list.filter(category=category)
    return render(request, "pages/jobs.html", {
        "jobs": job_list,
        "categories": CreativeProfile.CATEGORY_CHOICES,
        "selected_category": category or "",
    })


def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    already_applied = False
    if request.user.is_authenticated:
        already_applied = job.applications.filter(applicant=request.user).exists()
    return render(request, "konnect/job_detail.html", {"job": job, "already_applied": already_applied})


@login_required
def post_job(request):
    if request.method == "POST":
        job = Job.objects.create(
            poster=request.user,
            title=request.POST.get("title", ""),
            description=request.POST.get("description", ""),
            category=request.POST.get("category", "other"),
            budget=request.POST.get("budget") or None,
            deadline=request.POST.get("deadline") or None,
        )
        messages.success(request, "Your job has been posted.")
        return redirect("job_detail", pk=job.pk)

    return render(request, "konnect/post_job.html", {"categories": CreativeProfile.CATEGORY_CHOICES})


@login_required
def apply_job(request, pk):
    job = get_object_or_404(Job, pk=pk)

    if job.applications.filter(applicant=request.user).exists():
        messages.info(request, "You already applied to this job.")
        return redirect("job_detail", pk=pk)

    if request.method == "POST":
        JobApplication.objects.create(
            job=job,
            applicant=request.user,
            cover_letter=request.POST.get("cover_letter", ""),
        )
        notify(job.poster, f"{request.user.username} applied to your job: {job.title}", link=f"/jobs/{job.pk}/", category="application")
        messages.success(request, "Application submitted.")
        return redirect("job_detail", pk=pk)

    return render(request, "konnect/apply_job.html", {"job": job})


@login_required
def my_applications(request):
    applications = request.user.job_applications.select_related("job")
    return render(request, "konnect/my_applications.html", {"applications": applications})


def _suggested_connections(user):
    """Categorized 'People You May Know' style suggestions for the
    Collaborate page: excludes the user themselves and anyone they
    already have a collaboration request (pending/accepted/declined)
    with, so suggestions stay fresh."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    already_linked_ids = set(
        CollaborationRequest.objects.filter(from_user=user).values_list("to_user_id", flat=True)
    ) | set(
        CollaborationRequest.objects.filter(to_user=user).values_list("from_user_id", flat=True)
    )
    already_linked_ids.add(user.pk)

    base = User.objects.exclude(pk__in=already_linked_ids).select_related("creative_profile")

    return {
        "people_you_may_know": base.order_by("?")[:4],
        "suggested_creatives": base.filter(role="creative").select_related("creative_profile")[:4],
        "suggested_customers": base.filter(role="customer")[:4],
        "suggested_students": base.filter(role__in=["student", "instructor"])[:4],
    }


def collaborate(request):
    connections = None
    suggestions = None
    if request.user.is_authenticated:
        connections = CollaborationRequest.objects.filter(
            from_user=request.user
        ) | CollaborationRequest.objects.filter(to_user=request.user)
        connections = connections.order_by("-created_at")
        suggestions = _suggested_connections(request.user)

    creatives = CreativeProfile.objects.filter(is_available=True).exclude(
        user=request.user if request.user.is_authenticated else None
    )[:12]

    return render(request, "pages/collaborate.html", {
        "connections": connections,
        "creatives": creatives,
        "suggestions": suggestions,
    })


@login_required
@require_POST
def send_collaboration_request(request, user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    to_user = get_object_or_404(User, pk=user_id)

    if to_user == request.user:
        messages.error(request, "You can't collaborate with yourself.")
        return redirect("collaborate")

    collab, created = CollaborationRequest.objects.get_or_create(
        from_user=request.user, to_user=to_user,
        defaults={"message": request.POST.get("message", "")},
    )
    if created:
        notify(to_user, f"{request.user.username} sent you a collaboration request.", link="/collaborate/", category="collaboration")
        messages.success(request, f"Collaboration request sent to {to_user.username}.")
    else:
        messages.info(request, "You already sent a request to this user.")
    return redirect("collaborate")


@login_required
@require_POST
def respond_collaboration_request(request, pk, action):
    collab = get_object_or_404(CollaborationRequest, pk=pk, to_user=request.user)
    if action == "accept":
        collab.status = "accepted"
        notify(collab.from_user, f"{request.user.username} accepted your collaboration request.", link="/collaborate/", category="collaboration")
    elif action == "decline":
        collab.status = "declined"
    collab.save(update_fields=["status"])
    return redirect("collaborate")


@login_required
@require_POST
def toggle_saved_creative(request, pk):
    """Bookmark/unbookmark a creative — the Customer Dashboard's 'Saved Creatives'."""
    creative = get_object_or_404(CreativeProfile, pk=pk)
    saved, created = SavedCreative.objects.get_or_create(customer=request.user, creative=creative)
    if not created:
        saved.delete()
        messages.info(request, f"Removed {creative.user.username} from your saved creatives.")
    else:
        messages.success(request, f"Saved {creative.user.username} to your dashboard.")

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "dashboard"
    return redirect(next_url)


@login_required
def toggle_availability(request):
    """Quick on/off toggle for a creative's booking availability, used from
    the Creative Dashboard's Availability card."""
    profile = get_object_or_404(CreativeProfile, user=request.user)
    if request.method == "POST":
        profile.is_available = not profile.is_available
        note = request.POST.get("availability_note")
        if note is not None:
            profile.availability_note = note[:140]
        profile.save(update_fields=["is_available", "availability_note"])
        status = "open to new clients" if profile.is_available else "marked unavailable"
        messages.success(request, f"You're now {status}.")
    return redirect("dashboard")


@login_required
def leave_review(request, pk):
    """A client reviews a creative after a service request has been completed."""
    service_request = get_object_or_404(ServiceRequest, pk=pk, client=request.user, status="completed")

    if request.method == "POST":
        rating = request.POST.get("rating") or 5
        try:
            rating = max(1, min(5, int(rating)))
        except ValueError:
            rating = 5

        Review.objects.update_or_create(
            service_request=service_request,
            defaults={
                "reviewer": request.user,
                "creative": service_request.creative,
                "rating": rating,
                "comment": request.POST.get("comment", "").strip(),
            },
        )
        notify(
            service_request.creative.user,
            f"{request.user.username} left you a {rating}\u2605 review.",
            link="/dashboard/", category="portfolio_tip",
        )
        messages.success(request, "Thanks — your review has been posted.")

    return redirect("dashboard")


# ---------------------------------------------------------------------------
# Home Feed, Discover, Search, and project-level social interactions
# (like, comment, share, save, report) + Follow/Unfollow.
# ---------------------------------------------------------------------------

def home_feed(request):
    """The scrollable Home Feed — every visible project, most recent first.
    Logged-in users can toggle to 'Following' to see only creatives they
    follow."""
    projects = _visible_projects().annotate(
        like_total=Count("likes", distinct=True),
        comment_total=Count("comments", distinct=True),
    )

    show = request.GET.get("show", "all")
    if show == "following" and request.user.is_authenticated:
        followed_ids = Follow.objects.filter(follower=request.user).values_list("following_id", flat=True)
        projects = projects.filter(creative__user_id__in=followed_ids)

    category = request.GET.get("category")
    if category:
        projects = projects.filter(category=category)

    paginator = Paginator(projects.order_by("-created_at", "-pk"), 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    saved_ids = set()
    liked_ids = set()
    if request.user.is_authenticated:
        saved_ids = set(SavedProject.objects.filter(user=request.user).values_list("project_id", flat=True))
        liked_ids = set(ProjectLike.objects.filter(user=request.user).values_list("project_id", flat=True))

    return render(request, "dashboard/feed.html", {
        "page_obj": page_obj,
        "categories": PROJECT_CATEGORY_CHOICES,
        "selected_category": category or "",
        "show": show,
        "saved_ids": saved_ids,
        "liked_ids": liked_ids,
    })


def discover(request):
    """Browse: Trending, Latest, Most Liked, Most Viewed, and by Category."""
    tab = request.GET.get("tab", "trending")
    category = request.GET.get("category")

    projects = _visible_projects().annotate(
        like_total=Count("likes", distinct=True),
        comment_total=Count("comments", distinct=True),
    )
    if category:
        projects = projects.filter(category=category)

    if tab == "latest":
        projects = projects.order_by("-created_at")
    elif tab == "most_liked":
        projects = projects.order_by("-like_total", "-created_at")
    elif tab == "most_viewed":
        projects = projects.order_by("-views_count", "-created_at")
    else:  # trending — a simple recency-weighted engagement score
        tab = "trending"
        projects = projects.order_by("-like_total", "-comment_total", "-views_count", "-created_at")

    paginator = Paginator(projects, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    top_creatives = CreativeProfile.objects.filter(is_available=True).select_related("user").annotate(
        project_count=Count("portfolio_items", distinct=True)
    )
    if category:
        top_creatives = top_creatives.filter(
            portfolio_items__category=category,
            portfolio_items__is_reported_hidden=False,
        ).distinct()
    top_creatives = top_creatives.order_by("-profile_views")[:6]

    return render(request, "dashboard/discover.html", {
        "page_obj": page_obj,
        "tab": tab,
        "categories": PROJECT_CATEGORY_CHOICES,
        "selected_category": category or "",
        "top_creatives": top_creatives,
    })


def search(request):
    """Unified search across Creatives, Projects, Skills, and Categories."""
    query = (request.GET.get("q") or "").strip()

    creatives = []
    projects = []
    skills = []
    matched_categories = []

    if query:
        creatives = CreativeProfile.objects.filter(
            Q(headline__icontains=query) | Q(user__username__icontains=query)
            | Q(user__first_name__icontains=query) | Q(user__last_name__icontains=query)
            | Q(skills__name__icontains=query)
        ).select_related("user").distinct()[:20]

        projects = _visible_projects().filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        ).distinct()[:20]

        skills = Skill.objects.filter(name__icontains=query)[:15]

        matched_categories = [
            (value, label) for value, label in PROJECT_CATEGORY_CHOICES
            if query.lower() in label.lower()
        ]

    return render(request, "dashboard/search.html", {
        "query": query,
        "creatives": creatives,
        "projects": projects,
        "skills": skills,
        "matched_categories": matched_categories,
    })


@login_required
@require_POST
def toggle_like(request, pk):
    project = get_object_or_404(_visible_projects(), pk=pk)
    like, created = ProjectLike.objects.get_or_create(project=project, user=request.user)
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
        if request.user != project.creative.user:
            notify(
                project.creative.user,
                f"{request.user.username} liked your project \u201c{project.title}\u201d.",
                link=f"/projects/{project.pk}/", category="like",
            )

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"liked": liked, "like_count": project.like_count()})

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "home_feed"
    return redirect(next_url)


@login_required
def add_comment(request, pk):
    project = get_object_or_404(_visible_projects(), pk=pk)
    if request.method == "POST":
        text = request.POST.get("text", "").strip()
        if text:
            ProjectComment.objects.create(project=project, user=request.user, text=text[:500])
            if request.user != project.creative.user:
                notify(
                    project.creative.user,
                    f"{request.user.username} commented on \u201c{project.title}\u201d.",
                    link=f"/projects/{project.pk}/", category="comment",
                )
            messages.success(request, "Comment posted.")
    return redirect("project_detail", pk=pk)


@login_required
@require_POST
def delete_comment(request, pk):
    comment = get_object_or_404(ProjectComment, pk=pk, user=request.user)
    project_pk = comment.project_id
    comment.delete()
    return redirect("project_detail", pk=project_pk)


@login_required
@require_POST
def share_project(request, pk):
    project = get_object_or_404(_visible_projects(), pk=pk)
    ProjectShare.objects.create(project=project, user=request.user)
    if request.user != project.creative.user:
        notify(
            project.creative.user,
            f"{request.user.username} shared your project \u201c{project.title}\u201d.",
            link=f"/projects/{project.pk}/", category="share",
        )
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"share_count": project.share_count()})
    messages.success(request, "Project shared.")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "project_detail"
    return redirect(next_url)


@login_required
@require_POST
def toggle_save_project(request, pk):
    project = get_object_or_404(_visible_projects(), pk=pk)
    saved, created = SavedProject.objects.get_or_create(user=request.user, project=project)
    if not created:
        saved.delete()
        messages.info(request, "Removed from your saved projects.")
    else:
        messages.success(request, "Saved to your bookmarks.")
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "home_feed"
    return redirect(next_url)


@login_required
def report_project(request, pk):
    project = get_object_or_404(_visible_projects(), pk=pk)
    if request.method == "POST":
        ProjectReport.objects.create(
            project=project, reporter=request.user,
            reason=request.POST.get("reason", "other"),
            details=request.POST.get("details", ""),
        )
        messages.success(request, "Thanks — our team will review this project.")
        return redirect("project_detail", pk=pk)
    return render(request, "konnect/report_project.html", {"project": project})


@login_required
@require_POST
def toggle_follow(request, user_id):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    target = get_object_or_404(User, pk=user_id)

    if target == request.user:
        messages.error(request, "You can't follow yourself.")
        return redirect("public_profile", username=target.username)

    follow, created = Follow.objects.get_or_create(follower=request.user, following=target)
    if not created:
        follow.delete()
        messages.info(request, f"Unfollowed {target.username}.")
    else:
        notify(
            target, f"{request.user.username} started following you.",
            link=f"/u/{request.user.username}/", category="follow",
        )
        messages.success(request, f"You're now following {target.username}.")

    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or "public_profile"
    if next_url == "public_profile":
        return redirect("public_profile", username=target.username)
    return redirect(next_url)
