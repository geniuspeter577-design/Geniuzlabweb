from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.http import url_has_allowed_host_and_scheme
from django_ratelimit.decorators import ratelimit

from geniuzlab.validators import validate_image_upload
from .models import CustomerProfile

User = get_user_model()


@ratelimit(key="ip", rate="10/h", method="POST", block=True)
def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        role = request.POST.get("role", "customer")

        if not username or not email or not password:
            messages.error(request, "Please fill in all required fields.")
            return redirect("register")

        if confirm_password and password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect("register")

        if User.objects.filter(email=email).exists():
            messages.error(request, "An account with this email already exists.")
            return redirect("register")

        # Self-registration is limited to the three public-facing roles.
        # "instructor" and "admin" are staff-facing roles and must be
        # assigned by an admin (Django Admin) — never granted through the
        # public sign-up form, even if a request is crafted to include
        # role=instructor/admin directly.
        self_registerable_roles = {"customer", "creative", "student"}
        if role not in self_registerable_roles:
            role = "customer"

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
        )

        login(request, user)
        messages.success(request, "Welcome to GeniuzLab! Your account has been created.")
        return redirect("dashboard")

    return render(request, "accounts/register.html", {"role_choices": User.ROLE_CHOICES})


@ratelimit(key="ip", rate="20/h", method="POST", block=True)
@ratelimit(key="post:username", rate="8/h", method="POST", block=True)
def user_login(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)

        if user:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.POST.get("next") or request.GET.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
            ):
                return redirect(next_url)
            return redirect("dashboard")

        messages.error(request, "Incorrect password or login details. Please try again.")

    return render(request, "accounts/login.html")


@login_required
def user_logout(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect("home")


@login_required
def profile(request):
    customer_profile = None
    if request.user.role == "customer":
        customer_profile = CustomerProfile.objects.filter(user=request.user).first()
    return render(request, "accounts/profile.html", {
        "profile_user": request.user,
        "customer_profile": customer_profile,
    })


def public_profile(request, username):
    """Public professional profile — every Creative and Customer gets one
    (Students don't, since they aren't part of the creative marketplace/
    social layer). Unifies the 'Behance-style' creative portfolio view
    with a simpler public card for customers, all under one clickable
    /u/<username>/ URL used everywhere a name or avatar appears."""
    from django.http import Http404

    profile_user = get_object_or_404(User, username=username)
    if profile_user.role in ("student", "instructor"):
        raise Http404("This account doesn't have a public profile.")

    creative_profile = getattr(profile_user, "creative_profile", None)
    customer_profile = CustomerProfile.objects.filter(user=profile_user).first()

    is_following = False
    if request.user.is_authenticated and request.user != profile_user:
        from konnect.models import Follow
        is_following = Follow.objects.filter(follower=request.user, following=profile_user).exists()

    context = {
        "profile_user": profile_user,
        "creative_profile": creative_profile,
        "customer_profile": customer_profile,
        "is_following": is_following,
        "follower_count": profile_user.followers.count(),
        "following_count": profile_user.following.count(),
    }

    if creative_profile:
        context["portfolio_items"] = creative_profile.portfolio_items.filter(
            is_reported_hidden=False
        ).prefetch_related("media")

    return render(request, "accounts/public_profile.html", context)


@login_required
def edit_profile(request):
    user = request.user
    if request.method == "POST":
        new_email = request.POST.get("email", user.email).strip()
        if new_email != user.email and User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            messages.error(request, "That email address is already in use by another account.")
            return redirect("edit_profile")

        user.first_name = request.POST.get("first_name", user.first_name)
        user.last_name = request.POST.get("last_name", user.last_name)
        user.email = new_email
        user.phone = request.POST.get("phone", user.phone)
        user.bio = request.POST.get("bio", user.bio)
        user.phone_is_public = bool(request.POST.get("phone_is_public"))
        user.email_is_public = bool(request.POST.get("email_is_public"))

        avatar_file = request.FILES.get("avatar")
        if avatar_file:
            try:
                validate_image_upload(avatar_file)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
                return redirect("edit_profile")
            user.avatar = avatar_file
        elif request.POST.get("remove_avatar"):
            user.avatar = None

        cover_file = request.FILES.get("cover_photo")
        if cover_file:
            try:
                validate_image_upload(cover_file)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
                return redirect("edit_profile")
            user.cover_photo = cover_file
        elif request.POST.get("remove_cover_photo"):
            user.cover_photo = None

        user.save()
        messages.success(request, "Profile updated successfully.")
        return redirect("profile")

    return render(request, "accounts/edit_profile.html", {"profile_user": user})


@login_required
def edit_customer_profile(request):
    profile, _ = CustomerProfile.objects.get_or_create(user=request.user)

    if request.method == "POST":
        profile.profile_type = request.POST.get("profile_type", "personal")
        profile.company_name = request.POST.get("company_name", "")
        profile.save()
        messages.success(request, "Your customer profile has been saved.")
        return redirect("profile")

    service_requests = request.user.service_requests_sent.all()
    return render(request, "accounts/edit_customer_profile.html", {
        "profile": profile,
        "service_requests": service_requests,
    })
