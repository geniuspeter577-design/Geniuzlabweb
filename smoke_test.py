#!/usr/bin/env python
"""
GeniuzLab runtime smoke test.

This is a REAL runtime test, not static analysis: it boots Django,
spins up an in-memory-request test client, and makes actual HTTP
requests against every view in the app — following redirects,
submitting real forms, creating a real user via the Register page,
logging in, and hitting every page a logged-in user can reach.

It does not need a browser. It DOES need Django + this project's
dependencies installed (i.e. `pip install -r requirements.txt` first).

Usage:
    export GENIUZLAB_DEBUG=True
    python manage.py migrate
    python smoke_test.py

Exit code 0 = every page returned a healthy status (200/302 redirect
chain resolving to 200). Exit code 1 = at least one page errored
(500), 404'd, or the response body clearly rendered an error/debug
page. A full report prints either way.
"""
import os
import sys
import uuid

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "geniuzlab.settings")
os.environ.setdefault("GENIUZLAB_DEBUG", "True")

import django  # noqa: E402
django.setup()

from django.test import Client  # noqa: E402
from django.urls import reverse, NoReverseMatch  # noqa: E402

RESULTS = []  # (label, url, status, ok, note)


def check(client, label, url_name, args=None, method="get", data=None,
          expect_login_redirect=False, follow=True, expected_status=None):
    try:
        url = reverse(url_name, args=args or [])
    except NoReverseMatch as e:
        RESULTS.append((label, url_name, "N/A", False, f"NoReverseMatch: {e}"))
        return None

    try:
        if method == "get":
            resp = client.get(url, follow=follow)
        else:
            resp = client.post(url, data=data or {}, follow=follow)
    except Exception as e:
        RESULTS.append((label, url, "EXC", False, f"{type(e).__name__}: {e}"))
        return None

    status = resp.status_code
    ok = status < 400 if expected_status is None else status == expected_status
    note = ""

    if status >= 500:
        note = "SERVER ERROR"
    elif status == 404 and ok:
        note = "expected while feature is disabled"
    elif status == 404:
        note = "NOT FOUND"
    elif expect_login_redirect and status == 200 and resp.redirect_chain:
        # ended up somewhere after redirect(s) — fine, just note the chain
        note = f"redirected: {resp.redirect_chain}"

    # Django's debug 500/404 pages contain this marker; if DEBUG were
    # accidentally left on with a real error, this catches it even
    # when status_code reporting is patched by middleware.
    body = getattr(resp, "content", b"")
    if b"Traceback" in body or b"Exception Type" in body:
        ok = False
        note = "Traceback detected in response body"

    RESULTS.append((label, url, status, ok, note))
    return resp


def main():
    client = Client()

    print("=" * 70)
    print("GENIUZLAB RUNTIME SMOKE TEST")
    print("=" * 70)

    # ---- Anonymous / public pages ----
    check(client, "Homepage", "home")
    check(client, "About", "about")
    check(client, "Academy", "academy")
    check(client, "Course: Graphic Design", "graphic_design")
    check(client, "Course: Video Editing", "video_editing")
    check(client, "Course: AI Productivity", "ai_productivity")
    check(client, "Course: Web Development", "web_development")
    check(client, "Portfolio / Projects", "projects")
    check(client, "Featured Project: Brand Identity", "project_showcase", args=["brand-identity"])
    check(client, "Featured Project: Video Production", "project_showcase", args=["video-production"])
    check(client, "Featured Project: Web Development", "project_showcase", args=["web-development"])
    check(client, "Geniuz Graphics", "graphics")
    check(client, "GENIUZinMOTION", "motion")
    check(client, "GeniuzSubs (feature disabled)", "subs", expected_status=404)
    check(client, "Hire Creative (marketplace)", "hire_creative")
    check(client, "Browse Jobs", "jobs")
    check(client, "Collaborate", "collaborate")

    # ---- Auth pages (GET — page renders) ----
    check(client, "Login page", "login")
    check(client, "Register page", "register")
    check(client, "Forgot Password page", "password_reset")

    # ---- Dashboard while anonymous should redirect to login, not error ----
    check(client, "Dashboard (anonymous)", "dashboard", expect_login_redirect=True)

    # ---- Full register -> login -> dashboard user journey ----
    uname = f"smoketest_{uuid.uuid4().hex[:8]}"
    resp = check(
        client, "Register (POST, real account creation)", "register", method="post",
        data={
            "username": uname,
            "email": f"{uname}@example.com",
            "password": "TempPass123!",
            "confirm_password": "TempPass123!",
            "role": "customer",
        },
    )

    check(client, "Dashboard (after register/auto-login)", "dashboard")
    check(client, "Notifications", "notifications")

    # Logout, then log back in explicitly to test the Login form itself
    check(client, "Logout", "logout")
    check(
        client, "Login (POST, real credentials)", "login", method="post",
        data={"username": uname, "password": "TempPass123!"},
    )
    check(client, "Dashboard (after explicit login)", "dashboard")

    # ---- Register as Creative flow ----
    check(client, "Edit Creative Profile page", "edit_creative_profile")
    check(
        client, "Save Creative Profile (POST)", "edit_creative_profile", method="post",
        data={
            "headline": "Smoke Test Creative",
            "category": "web_development",
            "bio": "Automated smoke test profile.",
            "experience_years": "2",
            "location": "Lagos",
        },
    )

    # ---- Password reset (GET only — don't actually trigger email send loop) ----
    check(
        client, "Password Reset (POST, submit email)", "password_reset", method="post",
        data={"email": f"{uname}@example.com"},
    )

    # ---- AI Assistant backend ----
    try:
        url = reverse("assistant_ask")
        resp = client.post(
            url,
            data='{"message": "hi"}',
            content_type="application/json",
        )
        ok = resp.status_code == 200 and b"reply" in resp.content
        RESULTS.append(("AI Assistant (POST /assistant/ask/)", url, resp.status_code, ok, ""))
    except Exception as e:
        RESULTS.append(("AI Assistant (POST /assistant/ask/)", "assistant_ask", "EXC", False, str(e)))

    # ---- AI Hub (image + video generators) ----
    check(client, "AI Hub home", "ai_hub")
    check(client, "AI Image Generator page", "ai_hub_image")
    check(client, "AI Video Generator page", "ai_hub_video")

    # Without an API key configured, generation should fail gracefully
    # (not_configured: true) rather than 500 — this is the behavior the
    # "friendly configuration message instead of crashing" requirement
    # depends on, so it's worth a real runtime check.
    try:
        url = reverse("ai_hub_image_generate")
        resp = client.post(url, data='{"prompt": "a smoke test image"}', content_type="application/json")
        ok = resp.status_code == 200 and b'"ok"' in resp.content
        RESULTS.append(("AI Hub Image Generate (no key configured)", url, resp.status_code, ok, ""))
    except Exception as e:
        RESULTS.append(("AI Hub Image Generate (no key configured)", "ai_hub_image_generate", "EXC", False, str(e)))

    try:
        url = reverse("ai_hub_video_generate")
        resp = client.post(url, data='{"prompt": "a smoke test video"}', content_type="application/json")
        ok = resp.status_code == 200 and b'"ok"' in resp.content
        RESULTS.append(("AI Hub Video Generate (no key configured)", url, resp.status_code, ok, ""))
    except Exception as e:
        RESULTS.append(("AI Hub Video Generate (no key configured)", "ai_hub_video_generate", "EXC", False, str(e)))

    # ---- 404 handling sanity check ----
    resp = client.get("/this-page-does-not-exist-12345/")
    ok = resp.status_code == 404 and b"Traceback" not in resp.content
    RESULTS.append(("Unknown URL (should show custom 404)", "/this-page-does-not-exist-12345/", resp.status_code, ok, ""))

    # ---- Report ----
    print()
    print(f"{'PAGE':45} {'URL':30} {'STATUS':7} {'RESULT':6}  NOTES")
    print("-" * 110)
    all_ok = True
    for label, url, status, ok, note in RESULTS:
        if not ok:
            all_ok = False
        print(f"{label[:45]:45} {str(url)[:30]:30} {str(status):7} {'PASS' if ok else 'FAIL':6}  {note}")

    print()
    print("=" * 70)
    if all_ok:
        print("RESULT: ALL CHECKS PASSED — no runtime errors, no dead ends detected.")
    else:
        failed = [r for r in RESULTS if not r[3]]
        print(f"RESULT: {len(failed)} CHECK(S) FAILED — see FAIL rows above.")
    print("=" * 70)

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
