"""GeniuzLab Assistant — conversational engine with a clean seam for a
real LLM.

The rule-based engine below always runs first — it's what guarantees
"use the platform first" (Priority 1 of the assistant spec): a hire
request, a course question, or a navigation shortcut always gets a
real, deterministic answer with real platform links. It's
context-aware: it remembers what was just discussed in the session,
asks clarifying follow-up questions when a request is ambiguous, and
walks users through multi-step flows (like "become a creative").

If settings.OPENAI_API_KEY is set, get_reply() only calls out to OpenAI
when the rule-based engine couldn't match anything at all (recent
conversation history is included for real multi-turn context) — purely
to keep the conversation natural for open-ended teaching questions or
small talk that fall outside the rule set, instead of an immediate "I
don't understand." A question OpenAI is able to answer does not count
as an unresolved turn. Only when *both* the rules and the LLM (or no
LLM is configured at all) have nothing after repeated tries does the
assistant escalate to Customer Care — instead of behaving like a
stateless keyword/FAQ lookup, or becoming a WhatsApp forwarding bot.

Company, founder, services, pricing, FAQ, customer-care, business-hours,
and policy facts are NOT hardcoded here — they're read from
knowledge_base.json via kb.get_kb(), so updating what the assistant
knows only ever requires editing that one file. This module only holds
site-navigation shortcuts (jobs, wallet, dashboard, etc.) that map to
URL names, which aren't "knowledge" so much as routing, plus the
conversation-management logic itself.

CONTEXT SHAPE
-------------
The caller (views.ask) is responsible for persisting `context` across
requests (e.g. in the Django session) and passing it back in on every
call. It's a plain, JSON-serializable dict:

    {
        "history": [{"role": "user"|"assistant", "text": "..."}, ...],
        "last_intent": "course_graphic_design" | None,
        "last_course_key": "graphic_design" | None,
        "pending": {"type": "pricing_target" | "become_creative_check", ...} | None,
        "fallback_streak": 0,
    }

get_reply() always returns a dict:

    {
        "reply": "...",
        "intent": "...",
        "links": [{"label": ..., "url": ...}, ...],
        "quick_replies": ["Yes, I have an account", ...],
        "escalate": bool,
        "redirect_url": "https://wa.me/..." | None,
        "context": {...updated context to persist...},
    }
"""

import logging
import re

logger = logging.getLogger(__name__)

from django.conf import settings
from django.urls import NoReverseMatch, reverse

from .kb import get_kb

HISTORY_LIMIT = 12  # ~6 user/assistant turns of memory
FALLBACK_ESCALATE_AT = 2  # consecutive unresolved turns before we push Customer Care harder


def _kw_hit(lowered, keyword):
    """Whole-word/phrase match instead of a bare substring check, so a
    short keyword like 'hi' or 'no' doesn't false-positive inside an
    unrelated word (e.g. 'nothing', 'know'). Also accepts a simple
    trailing 's'/'es' so plural phrasing ("Logo Designers", "Branding
    Experts") still matches a singular keyword ("logo designer",
    "branding expert")."""
    return re.search(r"(?<!\w)" + re.escape(keyword) + r"(?:es|s)?(?!\w)", lowered) is not None


def _any_kw(lowered, keywords):
    return any(_kw_hit(lowered, kw) for kw in keywords)

# Site-navigation intents: keywords to match, reply text, and quick-reply
# links (label, url name). Order matters — first match wins, most
# specific intents first. These are pure routing shortcuts, not company
# knowledge, so they stay here rather than in the knowledge base.
SITE_INTENTS = [
    (
        "hire_creative",
        ["hire", "find a creative", "find creative", "need a designer", "need a video editor"],
        "I can help with that! You can browse and hire vetted creatives directly on GeniuzLab.",
        [("Browse Creatives", "hire_creative"), ("Post a Job", "post_job")],
    ),
    (
        "jobs",
        ["job", "jobs", "apply", "application", "gig"],
        "Looking for work or posting a job? Here's where to go:",
        [("Browse Jobs", "jobs"), ("My Applications", "my_applications")],
    ),
    (
        "academy",
        ["course", "academy", "learn", "class", "training", "study"],
        "Geniuz Academy has courses on Graphic Design, Video Editing, Web Development, and AI & Productivity.",
        [("Explore Academy", "academy")],
    ),
    (
        "vtu",
        ["airtime", "data plan", "subscription", "cable", "electricity", "vtu", "geniuzsubs", "buy data"],
        "GeniuzSubs handles airtime, data, cable TV, electricity bills, and exam pins — all from your wallet.",
        [("Open GeniuzSubs", "subs"), ("Fund Wallet", "wallet_home")],
    ),
    (
        "wallet",
        ["wallet", "balance", "fund my account", "top up"],
        "You can fund your wallet, check your balance, and review your transaction history here:",
        [("My Wallet", "wallet_home"), ("Transaction History", "transaction_history")],
    ),
    (
        "payments",
        ["payment", "pay", "receipt", "transaction", "paystack"],
        "All your payments and receipts are tracked in one place:",
        [("Payment History", "transaction_history")],
    ),
    (
        "messages",
        ["message", "chat with", "inbox", "conversation"],
        "You can message clients and creatives directly from your inbox.",
        [("Open Inbox", "inbox")],
    ),
    (
        "account",
        ["account", "profile"],
        "For account help — registering, logging in, or resetting your password:",
        [("Login", "login"), ("Register", "register"), ("My Profile", "profile")],
    ),
    (
        "dashboard",
        ["dashboard", "notifications", "my activity"],
        "Your dashboard has your profile, wallet, notifications, and recent activity all in one view.",
        [("Go to Dashboard", "dashboard"), ("Notifications", "notifications")],
    ),
    (
        "saved",
        ["saved project", "saved projects", "saved creative", "saved creatives", "my saved"],
        "Your saved creatives and projects are on your dashboard.",
        [("Go to Dashboard", "dashboard")],
    ),
    (
        "feed",
        ["home feed", "the feed", "open feed", "show me the feed", "is there a feed", "news feed"],
        "Yes! The Home Feed shows the latest work from every creative on GeniuzLab — you can like, comment, "
        "save, and share posts, or switch to Following to see only creatives you follow.",
        [("Open Feed", "home_feed"), ("Discover", "discover")],
    ),
    (
        "casual",
        [
            "how are you", "how're you doing", "what's up", "whats up",
            "i'm hungry", "im hungry", "i'm tired", "im tired",
            "i love this platform", "i love geniuzlab", "you're funny", "youre funny",
        ],
        "I'm doing great, thanks for asking! 😊 How can I help — hiring a creative, taking a course, "
        "or finding your way around GeniuzLab?",
        [],
    ),
    (
        "greeting",
        ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"],
        None,  # filled in dynamically from the knowledge base, see _greeting_reply()
        [("Hire a Creative", "hire_creative"), ("Explore Academy", "academy"), ("Browse Jobs", "jobs")],
    ),
    (
        "thanks",
        ["thank", "thanks", "appreciate"],
        "Anytime! Let me know if there's anything else you need.",
        [],
    ),
]

YES_KEYWORDS = ["yes", "yeah", "yep", "already", "i have", "i've registered", "i am registered", "sure", "correct"]
NO_KEYWORDS = ["no", "not yet", "nope", "haven't", "need to register", "don't have", "dont have"]

# ---------------------------------------------------------------------------
# Smart recommendation engine — "I need a logo designer" etc. should
# surface real, hireable creatives from the platform instead of just a
# generic "browse creatives" link (Priority 1: use the platform first).
# Each entry: (label, phrase keywords, CreativeProfile.category value or
# None, extra free-text search terms matched against skills/services/
# headline).
# ---------------------------------------------------------------------------
CREATIVE_HIRE_REQUESTS = [
    (
        "Logo Designers",
        ["logo designer", "logo design", "need a logo", "want a logo", "design a logo"],
        "graphic_design",
        ["logo"],
    ),
    (
        "Motion Graphics Designers",
        ["motion graphics designer", "motion graphics", "motion graphic designer", "animator", "animation designer"],
        "video_editing",
        ["motion graphics", "animation"],
    ),
    (
        "Branding Experts",
        ["branding expert", "branding designer", "need branding", "brand identity", "brand designer"],
        "graphic_design",
        ["branding", "brand identity"],
    ),
    (
        "Web Developers",
        ["web developer", "website developer", "need a website", "build a website", "web development"],
        "web_development",
        ["website", "web development"],
    ),
    (
        "Video Editors",
        ["video editor", "video editing", "edit my video", "need a video editor"],
        "video_editing",
        ["video editing"],
    ),
    (
        "Photographers",
        ["photographer", "photography", "need a photographer"],
        None,
        ["photography", "photo"],
    ),
    (
        "UI/UX Designers",
        ["ui/ux", "ui ux", "ui designer", "ux designer", "product designer", "user experience designer"],
        None,
        ["ui/ux", "ui design", "ux design", "product design"],
    ),
]


# ---------------------------------------------------------------------------
# Project-feed navigation — "show me recent logo projects", "trending
# works", "branding projects" should open the real Discover feed
# (filtered/sorted) instead of falling through to a generic reply
# (Priority 2: platform navigation). Each entry: (phrase keywords,
# PortfolioItem category value or None, discover 'tab' or None).
# ---------------------------------------------------------------------------
PROJECT_FEED_REQUESTS = [
    (["logo project", "logo projects", "logo work", "logo works"], "logo", None),
    (["branding project", "branding projects", "brand project", "brand projects"], "branding", None),
    (["flyer project", "flyer projects", "flyer work"], "flyer", None),
    (["motion graphics project", "motion graphics work", "motion graphics feed"], "motion_graphics", None),
    (["packaging project", "packaging projects"], "packaging", None),
    (["ui/ux project", "ui ux project", "ui/ux projects", "ui ux projects"], "ui_ux", None),
    (["video editing project", "video editing projects", "video project", "video projects"], "video_editing", None),
    (["web development project", "website project", "web project", "web projects"], "web_development", None),
    (["social media project", "social media projects"], "social_media", None),
    (["illustration project", "illustration projects", "illustration work"], "illustration", None),
    (["trending work", "trending works", "trending project", "trending projects", "what's trending", "whats trending"], None, "trending"),
    (["latest project", "latest projects", "latest work", "newest project"], None, "latest"),
    (["most liked project", "most liked work", "popular project", "popular projects"], None, "most_liked"),
]


# ---------------------------------------------------------------------------
# Context helpers
# ---------------------------------------------------------------------------

def default_context():
    return {
        "history": [],
        "last_intent": None,
        "last_course_key": None,
        "pending": None,
        "fallback_streak": 0,
    }


def _normalize_context(context):
    """Defensively fill in any missing keys so a partially-shaped or
    legacy session value never breaks the engine."""
    ctx = dict(context or {})
    base = default_context()
    for key, value in base.items():
        ctx.setdefault(key, value)
    if not isinstance(ctx.get("history"), list):
        ctx["history"] = []
    return ctx


def _remember_turn(ctx, user_text, reply_text):
    ctx["history"].append({"role": "user", "text": user_text})
    ctx["history"].append({"role": "assistant", "text": reply_text})
    if len(ctx["history"]) > HISTORY_LIMIT:
        ctx["history"] = ctx["history"][-HISTORY_LIMIT:]
    return ctx


# ---------------------------------------------------------------------------
# Reply builders (unchanged company/knowledge logic)
# ---------------------------------------------------------------------------

def _safe_url(name):
    try:
        return reverse(name)
    except NoReverseMatch:
        logger.warning("assistant: url_name %r does not resolve — dropping link", name)
        return None


def _build_links(pairs):
    """pairs: list of (label, url_name) tuples resolved via reverse().
    Any pair whose url_name fails to resolve is dropped rather than
    handed to the frontend as a dead '#' link."""
    links = []
    for label, name in pairs:
        url = _safe_url(name)
        if url:
            links.append({"label": label, "url": url})
    return links


def _external_links(pairs):
    """pairs: list of (label, raw_url) tuples used as-is, no reverse()."""
    return [{"label": label, "url": url} for label, url in pairs]


def _greeting_reply():
    kb = get_kb()
    return (
        f"Hey there! I'm the {kb['company']['name']} assistant. "
        f"I can help you hire a creative, take a course, manage your wallet, "
        f"or find your way around. What are you looking for?"
    )


def _founder_reply():
    kb = get_kb()
    founder = kb["founder"]
    roles = ", ".join(founder["roles"])
    text = (
        f"{kb['company']['name']} was founded by {founder['name']}, who serves as {founder['title']}. "
        f"{founder['name']} is also known as: {roles}."
    )
    return text, []


def _company_reply():
    kb = get_kb()
    links = [("Explore Academy", "academy"), ("Hire a Creative", "hire_creative"), ("Geniuz Graphics", "graphics")]
    return kb["company"]["description"], links


def _service_reply(service_key):
    kb = get_kb()
    service = kb["services"][service_key]
    return service["description"], [(service["label"], service["url_name"])]


def _pricing_reply():
    kb = get_kb()
    return kb["pricing"]["note"], [("Explore Academy", kb["pricing"]["url_name"])]


def _customer_care_reply():
    kb = get_kb()
    care = kb["customer_care"]
    numbers = " or ".join(care["call_numbers"])
    text = (
        f"I'll connect you with our support team immediately — you can also reach GeniuzLab Customer "
        f"Care by phone at {numbers}."
    )
    return text, []


def _business_hours_reply():
    kb = get_kb()
    return kb["business_hours"]["note"], []


def _recommend_creatives(category=None, terms=None, limit=3):
    """Query real, available CreativeProfile records matching a category
    and/or free-text terms (skills / services offered / headline),
    best creatives first (highest average review rating, then most
    profile views as a tiebreaker for creatives without reviews yet)."""
    from django.db.models import Avg, Q as DQ
    from apps.konnect.models import CreativeProfile

    qs = CreativeProfile.objects.filter(is_available=True)

    term_q = DQ()
    for term in (terms or []):
        term_q |= (
            DQ(skills__name__icontains=term)
            | DQ(services_offered__icontains=term)
            | DQ(headline__icontains=term)
        )

    if category and terms:
        qs = qs.filter(DQ(category=category) | term_q)
    elif category:
        qs = qs.filter(category=category)
    elif terms:
        qs = qs.filter(term_q)

    qs = (
        qs.distinct()
        .select_related("user")
        .annotate(avg_rating=Avg("reviews__rating"))
        .order_by("-avg_rating", "-profile_views")
    )
    return list(qs[:limit])


def _creative_profile_links(creatives):
    links = []
    for c in creatives:
        try:
            url = reverse("creative_detail", args=[c.pk])
        except NoReverseMatch:
            logger.warning("assistant: creative_detail does not resolve for pk=%s — dropping link", c.pk)
            continue
        links.append({"label": f"View {c.user.username}", "url": url})
    see_all = _safe_url("hire_creative")
    if see_all:
        links.append({"label": "See All", "url": see_all})
    return links


def _creative_recommend_reply(label, category=None, terms=None):
    """Builds the reply + links for a 'I need a <role>' request. Falls
    back to a generic browse-creatives pointer if nothing matches yet —
    still keeps the user on the platform rather than redirecting out."""
    creatives = _recommend_creatives(category=category, terms=terms)
    if not creatives:
        text = (
            f"I don't see any {label} available to hire right now, but new creatives join regularly — "
            f"you can browse the full {label} category and check back, or post a job so creatives can apply to you."
        )
        return text, _build_links([("Browse Creatives", "hire_creative"), ("Post a Job", "post_job")])

    lines = [f"Here are top {label} on GeniuzLab you can hire directly:"]
    for c in creatives:
        rating = f" · {c.avg_rating:.1f}★" if c.avg_rating else " · New"
        headline = c.headline or c.get_category_display()
        lines.append(f"• {c.user.username} — {headline}{rating}")
    lines.append("Tap a name below to view their profile and hire them.")
    text = "\n".join(lines)
    return text, _creative_profile_links(creatives)


def _project_feed_reply(category, tab):
    """Builds a reply that opens the real Discover feed, filtered by
    category and/or sorted by tab (trending/latest/most_liked) — so
    "show me recent logo projects" or "trending works" actually surfaces
    real platform content (Priority 2: platform navigation) instead of a
    generic answer."""
    discover_url = _safe_url("discover") or ""
    params = []
    if tab:
        params.append(f"tab={tab}")
    if category:
        params.append(f"category={category}")
    url = discover_url + ("?" + "&".join(params) if params else "")

    if category and tab:
        label = f"{tab.replace('_', ' ').title()} {category.replace('_', ' ').title()} projects"
    elif category:
        label = f"{category.replace('_', ' ').title()} projects"
    else:
        label = f"{tab.replace('_', ' ').title()} projects"

    text = f"Here's the {label.lower()} feed on GeniuzLab — real work from real creatives."
    links = [{"label": f"View {label}", "url": url}] if url else _build_links([("Browse Creatives", "hire_creative")])
    return text, links


LOCATION_SEARCH_RE = re.compile(
    r"(?:creative|creatives|designer|designers|developer|developers|editor|editors|photographer|photographers)"
    r".{0,20}?\bin\s+([a-zA-Z][a-zA-Z\s]{1,40})$"
)


def _location_search_reply(original_text):
    """Handles "Find a creative in <location>" style requests (Priority 3:
    search the platform) by actually querying available creatives whose
    location matches, instead of only recognising role/category keywords."""
    match = LOCATION_SEARCH_RE.search(original_text.strip().rstrip("?.!"))
    if not match:
        return None
    location = match.group(1).strip()
    if not location or len(location) < 2:
        return None

    from apps.konnect.models import CreativeProfile

    creatives = list(
        CreativeProfile.objects.filter(is_available=True, location__icontains=location)
        .select_related("user")
        .order_by("-profile_views")[:3]
    )
    if not creatives:
        text = (
            f"I couldn't find any available creatives based in {location} right now — "
            "you can browse all creatives and filter by location yourself, or post a job so "
            "creatives anywhere can apply."
        )
        return text, _build_links([("Browse Creatives", "hire_creative"), ("Post a Job", "post_job")])

    lines = [f"Here are creatives based in {location}:"]
    for c in creatives:
        headline = c.headline or c.get_category_display()
        lines.append(f"• {c.user.username} — {headline}")
    lines.append("Tap a name below to view their profile.")
    return "\n".join(lines), _creative_profile_links(creatives)


def _policies_reply():
    kb = get_kb()
    return kb["policies"]["note"], []


def _about_reply():
    kb = get_kb()
    company = kb["company"]
    text = f"{company['story']} Our mission: {company['mission']}"
    links = _build_links([("About GeniuzLab", company.get("about_url_name", "about"))])
    return text, links


def _register_reply():
    kb = get_kb()
    acc = kb["accounts"]["register"]
    return acc["description"], _build_links([(acc["label"], acc["url_name"])])


def _login_reply():
    kb = get_kb()
    acc = kb["accounts"]["login"]
    text = acc["description"] + " Forgotten your password? I can help with that too."
    return text, _build_links([(acc["label"], acc["url_name"]), ("Reset Password", kb["accounts"]["password_reset"]["url_name"])])


def _password_reset_reply():
    kb = get_kb()
    acc = kb["accounts"]["password_reset"]
    text = (
        f"{acc['description']} Enter the email on your account and follow the link sent to you. "
        "If it doesn't arrive within a few minutes, check spam or reach out to Customer Care."
    )
    return text, _build_links([(acc["label"], acc["url_name"])])


def _course_reply(course, lowered=""):
    text = f"{course['summary']} You'll cover: " + "; ".join(course["topics"]) + "."
    price_keywords = ["how much", "price", "cost", "fee", "fees"]
    if _any_kw(lowered, price_keywords):
        text += " For the current price, check the course page directly — it's always kept up to date there."
    return text, _build_links([(f"View {course['title']}", course["url_name"])])


def _faq_reply(faq):
    """FAQ entries without a stored 'answer' fall back to the company
    description (currently only the 'What is GeniuzLab?' entry)."""
    kb = get_kb()
    if faq.get("answer"):
        return faq["answer"], []
    return kb["company"]["description"], _build_links(
        [("Explore Academy", "academy"), ("Hire a Creative", "hire_creative")]
    )


def _fallback_reply():
    """When nothing matches, hand off to Customer Care rather than
    leaving the user with a dead-end 'I don't understand.'"""
    kb = get_kb()
    care = kb["customer_care"]
    text = (
        "I'm not totally sure I caught that. Here are the most common things people ask me about — "
        "or I can connect you with Customer Care directly."
    )
    links = _build_links(
        [("Hire a Creative", "hire_creative"), ("Explore Academy", "academy"), ("Browse Jobs", "jobs"), ("My Dashboard", "dashboard")]
    ) + _external_links([(care["whatsapp_button_label"], care["whatsapp_link"])])
    return text, links


def _escalation_suffix():
    kb = get_kb()
    care = kb["customer_care"]
    numbers = " or ".join(care["call_numbers"])
    return (
        f"\n\nIt looks like I might not be the fastest way to sort this out — "
        f"our Customer Care team can help directly on WhatsApp, or by phone at {numbers}."
    )


# ---------------------------------------------------------------------------
# Conversational / follow-up handling
# ---------------------------------------------------------------------------

def _match_course(kb, lowered):
    for course in kb["academy"]["courses"]:
        if course["title"].lower() in lowered or course["key"].replace("_", " ") in lowered:
            return course
    return None


def _match_service(kb, lowered):
    # "subs" (GeniuzSubs/VTU) is skipped while FEATURE_VTU_ENABLED is
    # False, so the assistant doesn't hand out a link to a disabled page.
    # The knowledge_base.json entry itself is untouched for when this is
    # re-enabled.
    candidates = ("graphics", "motion", "portfolio", "subs")
    if not getattr(settings, "FEATURE_VTU_ENABLED", False):
        candidates = tuple(c for c in candidates if c != "subs")
    for service_key in candidates:
        service = kb["services"][service_key]
        if service["label"].lower() in lowered or service_key in lowered:
            return service_key
    return None


def _handle_pending(ctx, lowered, kb):
    """If the assistant asked a clarifying question last turn, try to
    resolve the user's answer against that pending question first.
    Returns (reply, intent, links, quick_replies) or None if the
    pending state doesn't apply / couldn't be resolved, in which case
    normal intent matching should proceed."""
    pending = ctx.get("pending")
    if not pending:
        return None

    if pending["type"] == "pricing_target":
        course = _match_course(kb, lowered)
        if course:
            ctx["pending"] = None
            ctx["last_course_key"] = course["key"]
            reply, links = _course_reply(course, lowered)
            return reply, f"course_{course['key']}", links, []
        service_key = _match_service(kb, lowered)
        if service_key:
            ctx["pending"] = None
            reply, links = _service_reply(service_key)
            return reply, f"{service_key}_pricing", links, []
        # Couldn't resolve — drop the pending state and let normal
        # matching handle whatever they said instead of looping forever.
        ctx["pending"] = None
        return None

    if pending["type"] == "become_creative_check":
        ctx["pending"] = None
        if _any_kw(lowered, YES_KEYWORDS):
            text = (
                "Perfect — since you're already registered, head straight to your Creative Profile "
                "to add your portfolio, skills, experience, and pricing. Once it's complete, your dashboard "
                "will automatically switch to the Creative view."
            )
            return text, "become_creative_has_account", _build_links([("Set Up Creative Profile", "edit_creative_profile")]), []
        if _any_kw(lowered, NO_KEYWORDS):
            text = (
                "No problem — first create your GeniuzLab account, then come back here (or head straight "
                "to your dashboard) and I'll help you set up your Creative Profile with your portfolio and pricing."
            )
            return text, "become_creative_needs_account", _build_links([("Register", "register")]), []
        # Ambiguous answer — fall through to normal matching for this message.
        return None

    ctx["pending"] = None
    return None


def _rule_based_reply(text, ctx):
    lowered = text.lower()
    kb = get_kb()

    pending_result = _handle_pending(ctx, lowered, kb)
    if pending_result:
        return pending_result

    # Founder / CEO questions.
    founder_keywords = ["founder", "ceo", "who owns geniuzlab", "who created geniuzlab", "who runs geniuzlab", "otsaje"]
    if _any_kw(lowered, founder_keywords):
        reply, links = _founder_reply()
        return reply, "founder", links, []

    # About / story / mission / values.
    about_keywords = ["our story", "your story", "geniuzlab's mission", "our mission", "your mission", "our values", "your values", "core values", "why choose geniuzlab", "track record", "about page", "about us page"]
    if _any_kw(lowered, about_keywords):
        reply, links = _about_reply()
        return reply, "about", links, []

    # Password reset (check before the generic login/register keywords).
    if _any_kw(lowered, ["forgot my password", "forgot password", "reset my password", "reset password", "password reset", "cant remember password", "change my password"]):
        reply, links = _password_reset_reply()
        return reply, "password_reset", links, []

    # Registration.
    if _any_kw(lowered, ["register", "sign up", "create an account", "create account", "how do i join"]):
        reply, links = _register_reply()
        return reply, "register", links, []

    # Login.
    if _any_kw(lowered, ["login", "log in", "sign in", "cant log in", "can't log in"]):
        reply, links = _login_reply()
        return reply, "login", links, []

    # Individual course questions.
    course = _match_course(kb, lowered)
    if course:
        ctx["last_course_key"] = course["key"]
        reply, links = _course_reply(course, lowered)
        return reply, f"course_{course['key']}", links, []

    # Category-specific "I need a ___" hiring requests — checked before
    # the generic hire_creative/service/FAQ matching below so a request
    # like "I need a logo designer" surfaces real recommended creatives
    # instead of a generic browse link (Priority 1: use the platform).
    for label, keywords, category, terms in CREATIVE_HIRE_REQUESTS:
        if _any_kw(lowered, keywords):
            reply, links = _creative_recommend_reply(label, category=category, terms=terms)
            return reply, "hire_creative_recommend", links, []

    # "Find a creative in <location>" — real search, not just a category
    # match (Priority 3: search the platform).
    if "find" in lowered or "creative" in lowered or "designer" in lowered:
        location_result = _location_search_reply(text)
        if location_result:
            reply, links = location_result
            return reply, "location_search", links, []

    # "Show me recent logo projects", "trending works", "branding
    # projects" — open the real Discover feed (Priority 2: navigation).
    for keywords, category, tab in PROJECT_FEED_REQUESTS:
        if _any_kw(lowered, keywords):
            reply, links = _project_feed_reply(category, tab)
            return reply, "project_feed", links, []

    # "Take me to my portfolio" — the user's own portfolio dashboard.
    # Checked before the generic service-keyword match below, since that
    # one also recognises the bare word "portfolio" but for a different
    # destination (the public showcase feed, not this user's own page).
    # Deliberately does NOT match on the bare phrase "my portfolio" alone —
    # "list my portfolio" is how someone asks to *become* a creative
    # (handled further below) and must not be hijacked here.
    portfolio_nav_keywords = [
        "take me to my portfolio", "go to my portfolio", "show my portfolio",
        "view my portfolio", "open my portfolio", "my portfolio dashboard",
        "portfolio dashboard", "manage my portfolio", "edit my portfolio",
    ]
    if _any_kw(lowered, portfolio_nav_keywords):
        portfolio_url = _safe_url("portfolio_dashboard")
        links = [{"label": "My Portfolio", "url": portfolio_url}] if portfolio_url else []
        return "Here's your portfolio — manage your projects and showcase your work.", "portfolio_dashboard", links, []

    # Customer care / human handoff requests.
    care_keywords = [
        "customer care", "talk to a human", "speak to a human", "human agent",
        "whatsapp number", "phone number", "call you", "support number",
        "contact support", "contact us", "contact geniuzlab", "get in touch",
        "reach you", "connect me with support", "i have a complaint", "complaint",
        "report a bug", "report an issue", "payment failed", "my payment failed",
        "can't access my account", "cant access my account", "locked out of my account",
        "technical support", "need an administrator", "need admin", "speak to admin",
    ]
    if _any_kw(lowered, care_keywords):
        reply, links = _customer_care_reply()
        return reply, "customer_care", links, []

    # Business hours.
    if _any_kw(lowered, ["business hours", "opening hours", "what time do you open", "what time do you close", "are you open"]):
        return _business_hours_reply(), "business_hours", [], []

    # Policies (refunds, cancellations, privacy, etc.)
    if _any_kw(lowered, ["refund", "cancellation policy", "policy", "terms"]):
        return _policies_reply(), "policies", [], []

    # Pricing — ambiguous unless a course/service is named or one was
    # just discussed, in which case use conversation memory instead of
    # asking the user to repeat themselves.
    if _any_kw(lowered, ["price", "pricing", "how much does it cost", "cost of", "how much", "fee", "fees"]):
        service_key = _match_service(kb, lowered)
        if service_key:
            reply, links = _service_reply(service_key)
            return reply, f"{service_key}_pricing", links, []
        if ctx.get("last_course_key"):
            matched_course = next((c for c in kb["academy"]["courses"] if c["key"] == ctx["last_course_key"]), None)
            if matched_course:
                reply, links = _course_reply(matched_course, lowered)
                return reply, f"course_{matched_course['key']}_pricing", links, []
        ctx["pending"] = {"type": "pricing_target"}
        text_reply = "Sure — which course or service are you asking about? For example, Graphic Design, Video Editing, Web Development, or Hire a Creative."
        return text_reply, "pricing_clarify", _build_links([("Explore Academy", "academy"), ("Hire a Creative", "hire_creative")]), [
            "Graphic Design", "Video Editing", "Hire a Creative",
        ]

    # Company / about.
    if _any_kw(lowered, ["what is geniuzlab", "about geniuzlab", "what does geniuzlab do", "tell me about geniuzlab"]):
        reply, links = _company_reply()
        return reply, "company", links, []

    # Service-specific questions (graphics, motion, portfolio) that
    # aren't already covered by the navigation intents below.
    service_key = _match_service(kb, lowered)
    if service_key:
        reply, links = _service_reply(service_key)
        return reply, service_key, links, []

    # "Become a creative" gets a guided, step-by-step handoff instead of
    # a single static reply, since it's a multi-part flow in practice.
    # Checked before the FAQ loop below, since knowledge_base.json also
    # has a (single-shot) FAQ entry with overlapping keywords — the
    # guided flow should win.
    become_creative_keywords = ["become a creative", "join as a creative", "sell my services", "list my portfolio", "register as creative"]
    if _any_kw(lowered, become_creative_keywords):
        ctx["pending"] = {"type": "become_creative_check"}
        text_reply = "Great — let's get you set up. Do you already have a GeniuzLab account, or would this be a new registration?"
        return text_reply, "become_creative", [], ["Yes, I have an account", "No, I need to register"]

    # Remaining FAQ entries not already covered by a more specific
    # handler above (e.g. "how do I enroll", "fund my wallet", "contact us").
    for faq in kb["faqs"]:
        if faq.get("answer") and _any_kw(lowered, faq["keywords"]):
            reply, links = _faq_reply(faq)
            return reply, "faq", links, []

    # Site-navigation shortcuts.
    for intent, keywords, reply, links in SITE_INTENTS:
        # "vtu" (GeniuzSubs airtime/data/cable/electricity) is skipped
        # while FEATURE_VTU_ENABLED is False, so the assistant doesn't
        # suggest a page that's currently disabled. The entry itself is
        # left in SITE_INTENTS for when this is re-enabled.
        if intent == "vtu" and not getattr(settings, "FEATURE_VTU_ENABLED", False):
            continue
        if _any_kw(lowered, keywords):
            resolved_reply = _greeting_reply() if intent == "greeting" else reply
            return resolved_reply, intent, _build_links(links), []

    # Educational-sounding questions ("what is branding", "teach me
    # python", "explain motion graphics") that don't match a specific
    # course/service above still shouldn't be treated as a dead-end that
    # counts toward WhatsApp escalation (Priority 4: never redirect these
    # users). Give a graceful, still-on-platform answer instead.
    teach_keywords = [
        "what is", "what's", "whats", "explain", "teach me", "teach us",
        "how does", "how do i learn", "define", "definition of", "meaning of",
    ]
    if _any_kw(lowered, teach_keywords):
        text = (
            "I don't have a full lesson on that in this chat, but Geniuz Academy has structured courses "
            "that go deep on topics like this — Graphic Design, Video Editing, Web Development, and AI & "
            "Productivity. Worth a look?"
        )
        return text, "teach_redirect", _build_links([("Explore Academy", "academy")]), []

    reply, links = _fallback_reply()
    return reply, "fallback", links, []


def _try_openai_reply(text, user, ctx):
    """Best-effort call to OpenAI, only attempted when an API key is
    configured. Any failure here silently falls back to rule-based —
    the widget must never break just because an external API hiccups.
    Recent conversation history is included so the model has real
    multi-turn context, not just the latest message."""
    api_key = getattr(settings, "OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        from openai import OpenAI  # noqa: requires the `openai` package, not a hard dependency

        kb = get_kb()
        founder = kb["founder"]
        courses = "; ".join(f"{c['title']} — {c['summary']}" for c in kb["academy"]["courses"])
        services = "; ".join(f"{s['label']} — {s['description']}" for s in kb["services"].values())
        system_prompt = (
            f"You are the {kb['company']['name']} website assistant. A rule-based layer already handles "
            f"hiring requests, navigation, courses, and FAQs with real platform links — you are only being "
            f"asked because the user's message didn't match any of that, so you're filling in for open-ended "
            f"conversation: teaching/explaining a concept, or ordinary small talk. Sound like a warm, natural "
            f"human support representative, not a search engine. {kb['company']['description']} "
            f"{kb['company']['story']} The founder and CEO is {founder['name']} ({', '.join(founder['roles'])}). "
            f"{founder['bio']} Geniuz Academy courses: {courses}. Other GeniuzLab services: {services}. "
            "If a teaching question relates to one of those courses, mention the course briefly, but don't "
            "invent platform features or links yourself — you have no ability to generate them here. "
            "Maintain context from earlier in this conversation — don't ask the user to repeat something "
            "they already told you. Never suggest WhatsApp or Customer Care yourself — human escalation is "
            "handled separately, outside of what you generate. "
            "Answer briefly, naturally, and professionally. Never invent prices — point users to the "
            "relevant course/service page for current pricing."
        )
        messages = [{"role": "system", "content": system_prompt}]
        for turn in ctx.get("history", [])[-HISTORY_LIMIT:]:
            role = "assistant" if turn.get("role") == "assistant" else "user"
            messages.append({"role": role, "content": turn.get("text", "")})
        messages.append({"role": "user", "content": text})

        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=350,
        )
        reply_text = response.choices[0].message.content.strip()
        return reply_text, "openai", [], []
    except Exception:
        return None


def get_reply(user, text, context=None):
    """Returns a dict: {reply, intent, links, quick_replies, escalate, context}.

    `context` should be whatever this function returned last time for
    this session (or None on the first turn) — the caller is
    responsible for persisting it (e.g. in the Django session).

    Rule-based matching always runs first — it's what guarantees
    "use the platform first" (Priority 1): a hire request, a course
    question, or a navigation shortcut always gets a real, deterministic
    answer with real links, never something an LLM might paraphrase away.
    OpenAI (if configured) is only consulted when the rule-based engine
    couldn't match anything at all — i.e. purely to have a natural,
    on-platform conversation about something outside the rule set
    (open-ended teaching questions, small talk) instead of an immediate
    "I don't understand." A question OpenAI is able to answer is not
    counted as an unresolved turn, so it never nudges the user toward
    WhatsApp — escalation is reserved for when *both* the rules and the
    LLM have nothing.
    """
    ctx = _normalize_context(context)

    reply, intent, links, quick_replies = _rule_based_reply(text, ctx)

    if intent == "fallback":
        openai_result = _try_openai_reply(text, user, ctx)
        if openai_result:
            reply, intent, links, quick_replies = openai_result

    if intent == "fallback":
        ctx["fallback_streak"] = ctx.get("fallback_streak", 0) + 1
    else:
        ctx["fallback_streak"] = 0

    escalate = ctx["fallback_streak"] >= FALLBACK_ESCALATE_AT
    redirect_url = None

    if intent == "customer_care":
        # Explicit human-handoff request (Priority 5) — reply naturally,
        # no buttons, automatic redirect after a short pause. This fires
        # immediately on request, independent of the fallback streak.
        links = []
        quick_replies = []
        redirect_url = get_kb()["customer_care"]["whatsapp_link"]
    elif escalate and intent == "fallback":
        reply = reply + _escalation_suffix()
        # Escalation hands off to a human — no buttons to tap, just an
        # automatic redirect to WhatsApp after a short pause.
        links = []
        quick_replies = []
        redirect_url = get_kb()["customer_care"]["whatsapp_link"]

    ctx["last_intent"] = intent
    ctx = _remember_turn(ctx, text, reply)

    return {
        "reply": reply,
        "intent": intent,
        "links": links,
        "quick_replies": quick_replies,
        "escalate": escalate,
        "redirect_url": redirect_url,
        "context": ctx,
    }
