from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render, get_object_or_404

# Curated case studies used by the three signature "Featured Projects" cards
# on the homepage (Brand Identity, Video Production, Web Development). These
# are GeniuzLab-authored showcase pieces, not user-submitted portfolio items,
# so they live here rather than in the database.
PROJECT_SHOWCASE = {
    "brand-identity": {
        "title": "Brand Identity",
        "tag": "🏷️ Geniuz Graphics",
        "image": "images/generated/portfolio_branding.png",
        "summary": "Professional branding, logo design and complete visual identity solutions.",
        "details": [
            "Full visual identity system — logo, colour palette, and typography.",
            "Social media templates and marketing collateral built for consistency.",
            "Delivered by GeniuzLab's vetted graphic design creatives on Geniuz Graphics.",
        ],
        "service_url_name": "graphics",
        "service_label": "Explore Geniuz Graphics",
    },
    "video-production": {
        "title": "Video Production",
        "tag": "🎬 GENIUZinMOTION",
        "image": "images/generated/portfolio_video.png",
        "summary": "Cinematic editing, commercials and storytelling projects.",
        "details": [
            "Cinematic editing with colour grading, sound design, and motion graphics.",
            "Short-form and long-form cuts built for retention across platforms.",
            "Delivered by GeniuzLab's video editing creatives on GENIUZinMOTION.",
        ],
        "service_url_name": "motion",
        "service_label": "Explore GENIUZinMOTION",
    },
    "web-development": {
        "title": "Web Development",
        "tag": "💻 GeniuzLab Creatives",
        "image": "images/generated/portfolio_webdev.png",
        "summary": "Modern websites and digital solutions built for brands.",
        "details": [
            "Responsive, modern websites built with today's frontend and backend tools.",
            "Built for performance, accessibility, and real business goals.",
            "Delivered by GeniuzLab's web development creatives — hire one via GeniuzKonnect.",
        ],
        "service_url_name": "hire_creative",
        "service_label": "Hire a Web Developer",
    },
}


def home(request):
    # The "Featured Projects" / Graphics section on the homepage: each slot
    # shows the latest live project uploaded in that category, and only
    # falls back to a curated GeniuzLab showcase card if nothing has been
    # uploaded in that category yet — so the section is never empty on a
    # fresh install, but fills in with real creative work automatically.
    slot_categories = [
        ("branding", "brand-identity"),
        ("video_editing", "video-production"),
        ("web_development", "web-development"),
    ]
    cards = []
    try:
        from apps.konnect.models import PortfolioItem

        for category, fallback_slug in slot_categories:
            project = (
                PortfolioItem.objects.filter(category=category, is_reported_hidden=False)
                .select_related("creative__user")
                .order_by("-created_at")
                .first()
            )
            if project:
                cards.append({"is_live": True, "project": project})
            else:
                cards.append({"is_live": False, "showcase": {**PROJECT_SHOWCASE[fallback_slug], "slug": fallback_slug}})
    except Exception:
        cards = [
            {"is_live": False, "showcase": {**PROJECT_SHOWCASE[slug], "slug": slug}}
            for _, slug in slot_categories
        ]

    return render(request, "dashboard/home.html", {"graphics_cards": cards})


def about(request):
    return render(request, "dashboard/about.html")


def project_showcase(request, slug):
    project = PROJECT_SHOWCASE.get(slug)
    if project is None:
        raise Http404("Project not found")
    return render(request, "dashboard/project_showcase.html", {"project": {**project, "slug": slug}})


def _profile_completion(user, creative_profile, customer_profile=None):
    """Simple weighted checklist so users can see what's left to finish."""
    checks = [
        bool(user.first_name),
        bool(user.last_name),
        bool(user.email),
        bool(user.phone),
        bool(user.bio),
        bool(user.avatar),
    ]
    if creative_profile:
        checks += [
            bool(creative_profile.headline),
            bool(user.avatar or creative_profile.avatar),
            bool(creative_profile.skills.exists()),
            bool(creative_profile.portfolio_items.exists()),
            bool(creative_profile.hourly_rate),
        ]
    elif user.role == "customer":
        checks.append(bool(customer_profile and customer_profile.company_name) or bool(customer_profile))
    else:
        checks.append(False)
    done = sum(1 for c in checks if c)
    return round((done / len(checks)) * 100)


@login_required
def dashboard(request):
    context = {}

    try:
        from apps.wallet.models import Wallet
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        context["wallet_balance"] = wallet.balance
        context["wallet_entries"] = wallet.entries.all()[:4]
    except Exception:
        context["wallet_balance"] = 0
        context["wallet_entries"] = []

    try:
        context["unread_notifications"] = request.user.notifications.filter(is_read=False).count()
        context["notifications_preview"] = request.user.notifications.all()[:5]
    except Exception:
        context["unread_notifications"] = 0
        context["notifications_preview"] = []

    creative_profile = None
    try:
        from apps.konnect.models import CreativeProfile, Job, JobApplication, ServiceRequest
        creative_profile = CreativeProfile.objects.filter(user=request.user).first()
        context["creative_profile"] = creative_profile
        context["jobs_posted"] = Job.objects.filter(poster=request.user).count()
        context["applications_count"] = JobApplication.objects.filter(applicant=request.user).count()
        if creative_profile:
            context["portfolio_count"] = creative_profile.portfolio_items.count()
            context["service_requests_count"] = ServiceRequest.objects.filter(creative=creative_profile).count()
        else:
            context["portfolio_count"] = 0
            context["service_requests_count"] = 0
    except Exception:
        context["creative_profile"] = None
        context["jobs_posted"] = 0
        context["applications_count"] = 0
        context["portfolio_count"] = 0
        context["service_requests_count"] = 0

    try:
        context["conversations_count"] = request.user.conversations.count()
    except Exception:
        context["conversations_count"] = 0

    customer_profile = None
    if request.user.role == "customer":
        try:
            from apps.accounts.models import CustomerProfile
            customer_profile = CustomerProfile.objects.filter(user=request.user).first()
        except Exception:
            customer_profile = None
    context["customer_profile"] = customer_profile

    context["profile_completion"] = _profile_completion(request.user, creative_profile, customer_profile)

    try:
        from apps.subs.models import UserSubscription
        context["active_subscription"] = UserSubscription.objects.filter(
            user=request.user, is_active=True
        ).select_related("plan").first()
    except Exception:
        context["active_subscription"] = None

    role = request.user.role

    # --- Customer-specific: Orders + Saved Creatives -----------------------
    if role == "customer":
        try:
            from apps.konnect.models import ServiceRequest, SavedCreative
            context["orders"] = ServiceRequest.objects.filter(
                client=request.user
            ).select_related("creative__user")[:8]
            context["saved_creatives"] = SavedCreative.objects.filter(
                customer=request.user
            ).select_related("creative__user")
        except Exception:
            context["orders"] = []
            context["saved_creatives"] = []

    # --- Creative-specific: Earnings, Analytics, Client Requests, Reviews --
    if role == "creative" and creative_profile:
        try:
            from apps.konnect.models import ServiceRequest
            from apps.payments.models import Transaction

            client_requests = ServiceRequest.objects.filter(
                creative=creative_profile
            ).select_related("client")
            context["client_requests"] = client_requests[:8]
            context["pending_requests_count"] = client_requests.filter(status="pending").count()

            earnings = Transaction.objects.filter(
                user=request.user, purpose="service", status="success"
            )
            context["earnings_total"] = sum((t.amount for t in earnings), start=0)
            context["earnings_recent"] = earnings[:5]

            context["reviews"] = creative_profile.reviews.select_related("reviewer")[:6]
            context["average_rating"] = creative_profile.average_rating()
            context["review_count"] = creative_profile.review_count()
        except Exception:
            context["client_requests"] = []
            context["pending_requests_count"] = 0
            context["earnings_total"] = 0
            context["earnings_recent"] = []
            context["reviews"] = []
            context["average_rating"] = None
            context["review_count"] = 0

    # --- Student-specific: Courses, Progress, Assignments, Certificates,
    #     Community ---------------------------------------------------------
    if role in ("student", "instructor"):
        try:
            from apps.academy.models import (
                Assignment, AssignmentSubmission, Certificate,
                CommunityPost, Enrollment, EnrollmentPayment, ensure_default_courses,
            )

            courses = ensure_default_courses()
            enrollments = {
                e.course_id: e for e in Enrollment.objects.filter(user=request.user)
            }
            pending_payments = {
                p.course_id: p for p in EnrollmentPayment.objects.filter(
                    user=request.user, status="pending"
                )
            }
            course_progress = []
            for course in courses:
                enrollment = enrollments.get(course.id)
                course_progress.append({
                    "course": course,
                    "enrollment": enrollment,
                    "progress": enrollment.progress_percent if enrollment else 0,
                    "enrolled": enrollment is not None,
                    "payment_pending": course.id in pending_payments,
                    "has_modules": course.modules.filter(status="published").exists(),
                })
            context["course_progress"] = course_progress
            context["enrolled_count"] = len(enrollments)

            submitted_ids = set(
                AssignmentSubmission.objects.filter(user=request.user).values_list("assignment_id", flat=True)
            )
            assignments = Assignment.objects.filter(
                course_id__in=enrollments.keys()
            ).select_related("course")[:8] if enrollments else []
            context["assignments"] = [
                {"assignment": a, "submitted": a.id in submitted_ids} for a in assignments
            ]

            context["certificates"] = Certificate.objects.filter(user=request.user).select_related("course")
            context["community_posts"] = CommunityPost.objects.select_related("user")[:8]

            # "Skills learned" — derived from completed courses, no extra
            # tagging model needed since Course already models each skill area.
            context["skills_learned"] = [
                cp["course"].title for cp in course_progress if cp["progress"] >= 100
            ]
        except Exception:
            context["course_progress"] = []
            context["enrolled_count"] = 0
            context["assignments"] = []
            context["certificates"] = []
            context["community_posts"] = []
            context["skills_learned"] = []

    # Recent activity — merge a few different sources into one feed, newest first.
    activity = []
    for n in context["notifications_preview"]:
        activity.append({"icon": "fa-bell", "text": n.message, "time": n.created_at})
    for e in context["wallet_entries"]:
        verb = "Wallet credited" if e.type == "credit" else "Wallet debited"
        activity.append({
            "icon": "fa-wallet",
            "text": f"{verb}: ₦{e.amount}" + (f" — {e.description}" if e.description else ""),
            "time": e.created_at,
        })
    activity.sort(key=lambda a: a["time"], reverse=True)
    context["recent_activity"] = activity[:6]

    # Same shared data, three presentations — each role sees the sections
    # most relevant to them without losing anything the old single dashboard
    # showed (the "generic" template below is used as a fallback).
    template_by_role = {
        "student": "dashboard/dashboard_student.html",
        # Instructor accounts are admin-managed for now and have no student
        # enrollments/assignments of their own — showing them the student
        # dashboard (enroll/pay-for-a-course prompts, etc.) is a broken
        # experience for that role, so they get an honest "still being
        # built" placeholder instead until a real instructor dashboard ships.
        "instructor": "dashboard/dashboard_instructor.html",
        "creative": "dashboard/dashboard_creative.html",
        "customer": "dashboard/dashboard_customer.html",
    }
    template = template_by_role.get(request.user.role, "dashboard/dashboard.html")

    return render(request, template, context)


def graphic_design(request):
    # Old hardcoded course page — now redirects to the dynamic, database-driven
    # course detail page. Kept here (rather than removed) so the existing
    # /courses/graphic-design/ URL and its 'graphic_design' url name keep working.
    return redirect("course_detail", slug="graphic-design", permanent=True)


def video_editing(request):
    return redirect("course_detail", slug="video-editing", permanent=True)


def ai_productivity(request):
    return redirect("course_detail", slug="ai-productivity", permanent=True)


def web_development(request):
    return redirect("course_detail", slug="web-development", permanent=True)


def graphics(request):
    return render(request, "pages/graphics.html")


def projects(request):
    try:
        from apps.konnect.models import PortfolioItem
        items = PortfolioItem.objects.filter(is_reported_hidden=False).select_related(
            "creative__user"
        ).prefetch_related("media")[:24]
    except Exception:
        items = []
    return render(request, "dashboard/projects.html", {"portfolio_items": items})


def project_detail(request, pk):
    from apps.konnect.models import PortfolioItem, Follow, SavedProject

    item = get_object_or_404(
        PortfolioItem.objects.filter(is_reported_hidden=False).select_related("creative__user").prefetch_related(
            "media", "comments__user"
        ),
        pk=pk,
    )
    item.register_view(request.user)

    other_works = item.creative.portfolio_items.exclude(pk=item.pk).filter(
        is_reported_hidden=False
    )[:6]

    is_following = False
    is_saved = False
    if request.user.is_authenticated:
        is_following = Follow.objects.filter(
            follower=request.user, following=item.creative.user
        ).exists()
        is_saved = SavedProject.objects.filter(user=request.user, project=item).exists()

    return render(request, "dashboard/project_detail.html", {
        "item": item,
        "other_works": other_works,
        "is_following": is_following,
        "is_saved": is_saved,
        "is_liked": item.is_liked_by(request.user),
    })


def robots_txt(request):
    """Basic robots.txt — allow crawling of the public site, keep
    authenticated-only areas (dashboard, chat, wallet, admin) out of the
    index. Served as plain text with no DB/template dependency so it can
    never 500."""
    lines = [
        "User-agent: *",
        "Allow: /",
        "Disallow: /admin/",
        "Disallow: /dashboard/",
        "Disallow: /chat/",
        "Disallow: /wallet/",
        "Disallow: /notifications/",
        "Disallow: /vtu/",
        "Disallow: /payments/",
        "Disallow: /automation/",
        "Disallow: /ai-hub/",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")
