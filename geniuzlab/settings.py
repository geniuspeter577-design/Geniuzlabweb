"""
Django settings for geniuzlab project.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Optional .env support — safe no-op if python-dotenv isn't installed.
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


def env_bool(key, default=False):
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


# SECURITY WARNING: keep the secret key used in production secret!
# In production, set GENIUZLAB_SECRET_KEY as an environment variable.
_INSECURE_DEV_KEY = "django-insecure-2%u)3(^#nzf4ap=i&s*cih&qv2=@n_=3oa2e78f3^ms@83&mb7"
SECRET_KEY = os.environ.get("GENIUZLAB_SECRET_KEY", "")
if not SECRET_KEY:
    if env_bool("GENIUZLAB_DEBUG", False):
        SECRET_KEY = _INSECURE_DEV_KEY
    else:
        raise RuntimeError(
            "GENIUZLAB_SECRET_KEY environment variable is required in production. "
            "Generate one with: python -c \"from django.core.management.utils import "
            "get_random_secret_key; print(get_random_secret_key())\""
        )

# SECURITY WARNING: don't run with debug turned on in production!
# Default is now False — you must explicitly set GENIUZLAB_DEBUG=True for local dev.
DEBUG = env_bool("GENIUZLAB_DEBUG", False)

_allowed_hosts_raw = os.environ.get("GENIUZLAB_ALLOWED_HOSTS", "")
if not _allowed_hosts_raw and DEBUG:
    _allowed_hosts_raw = "localhost,127.0.0.1"
ALLOWED_HOSTS = [h.strip() for h in _allowed_hosts_raw.split(",") if h.strip()]

if not DEBUG and not ALLOWED_HOSTS:
    raise RuntimeError(
        "GENIUZLAB_ALLOWED_HOSTS must be set (comma-separated) when GENIUZLAB_DEBUG is False."
    )


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'accounts',
    'academy',
    'konnect',
    'motion',
    'subs',
    'wallet',
    'payments',
    'chat',
    'notifications',
    'dashboard',
    'automation',
    'assistant',
    'ai_hub',
    'vtu',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'accounts.middleware.PresenceMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'geniuzlab.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'automation.context_processors.automation_context',
                'geniuzlab.context_processors.feature_flags',
            ],
        },
    },
]

WSGI_APPLICATION = 'geniuzlab.wsgi.application'


# Database
# For production, point GENIUZLAB_DATABASE_URL at Postgres/MySQL and wire it
# up with dj-database-url (kept as sqlite by default so this still runs with
# zero extra setup).

# Database
# Uses Postgres in production when GENIUZLAB_DATABASE_URL is set (e.g.
# postgres://user:pass@host:5432/dbname). Falls back to sqlite so this still
# runs with zero extra setup locally.
_database_url = os.environ.get("GENIUZLAB_DATABASE_URL", "")
if _database_url:
    import dj_database_url
    DATABASES = {
        "default": dj_database_url.parse(_database_url, conn_max_age=600, ssl_require=not DEBUG)
    }
else:
    if not DEBUG:
        raise RuntimeError(
            "GENIUZLAB_DATABASE_URL must be set in production (sqlite is not safe for "
            "concurrent production traffic)."
        )
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }


# Password validation

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


# Internationalization

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Lagos'
USE_I18N = True
USE_TZ = False


# Static & media files

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / "media"

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}
if os.environ.get("GENIUZLAB_REDIS_CACHE_URL"):
    CACHES["default"] = {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": os.environ["GENIUZLAB_REDIS_CACHE_URL"],
    }
RATELIMIT_USE_CACHE = "default"

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'

LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'home'

MESSAGE_TAGS = {}

MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB — avatars, cover photos, portfolio images

# Chat attachments (documents/source files delivered as part of a job) need
# more headroom than a profile picture — .AI/.PSD files routinely run well
# past 5MB. Both are overridable via env var without touching code.
MAX_CHAT_ATTACHMENT_SIZE = int(
    os.environ.get("GENIUZLAB_MAX_CHAT_ATTACHMENT_SIZE", 25 * 1024 * 1024)
)  # 25MB default
MAX_VIDEO_UPLOAD_SIZE = int(
    os.environ.get("GENIUZLAB_MAX_VIDEO_UPLOAD_SIZE", 60 * 1024 * 1024)
)  # 60MB default — chat video attachments and portfolio video uploads


# ---------------------------------------------------------------------------
# Email / password reset
# By default (DEBUG=True) emails are printed to the console so the reset
# flow works out of the box with zero setup. Set GENIUZLAB_EMAIL_HOST (and
# friends) in the environment to send real emails via SMTP in production.
#
# IMPORTANT — the #1 cause of "users never receive the email" reports is
# simply that GENIUZLAB_EMAIL_HOST was never set on the deployed server, so
# EMAIL_BACKEND silently falls back to the console backend below: the email
# *is* generated correctly, it just gets printed to the server's stdout/log
# instead of being handed to an SMTP relay. A system check (below) now turns
# that silent fallback into a loud, impossible-to-miss error whenever
# DEBUG=False, instead of leaving it invisible until someone reports a bug.
# ---------------------------------------------------------------------------
EMAIL_HOST = os.environ.get("GENIUZLAB_EMAIL_HOST", "")

if EMAIL_HOST:
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_PORT = int(os.environ.get("GENIUZLAB_EMAIL_PORT", "587"))
    # Gmail/most providers' SSL port (465) needs EMAIL_USE_SSL instead of
    # EMAIL_USE_TLS — auto-detect from the port so a common misconfiguration
    # (TLS flag left on with port 465) can't produce a silent connect failure.
    if EMAIL_PORT == 465:
        EMAIL_USE_SSL = env_bool("GENIUZLAB_EMAIL_USE_SSL", True)
        EMAIL_USE_TLS = False
    else:
        EMAIL_USE_TLS = env_bool("GENIUZLAB_EMAIL_USE_TLS", True)
        EMAIL_USE_SSL = False
    EMAIL_HOST_USER = os.environ.get("GENIUZLAB_EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("GENIUZLAB_EMAIL_HOST_PASSWORD", "")
    # Without a timeout, a flaky/blocked SMTP connection hangs the whole
    # request (registration, password reset, contact form) until the OS
    # socket timeout kicks in, which can be minutes.
    EMAIL_TIMEOUT = int(os.environ.get("GENIUZLAB_EMAIL_TIMEOUT", "10"))
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEFAULT_FROM_EMAIL = os.environ.get("GENIUZLAB_DEFAULT_FROM_EMAIL", "GeniuzLab <no-reply@geniuzlab.com>")
SERVER_EMAIL = os.environ.get("GENIUZLAB_SERVER_EMAIL", DEFAULT_FROM_EMAIL)

# Password reset links expire after 3 days.
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24 * 3


from django.core.checks import Warning as _CheckWarning, Error as _CheckError, register as _register_check


@_register_check
def _email_backend_check(app_configs, **kwargs):
    """Surface email misconfiguration in `python manage.py check` instead of
    letting it fail silently in production — this is exactly the class of
    bug behind 'user entered the right email but never got anything'."""
    issues = []
    if not DEBUG and EMAIL_BACKEND == "django.core.mail.backends.console.EmailBackend":
        issues.append(
            _CheckError(
                "No outbound email transport is configured for production.",
                hint=(
                    "Set GENIUZLAB_EMAIL_HOST (plus GENIUZLAB_EMAIL_HOST_USER / "
                    "GENIUZLAB_EMAIL_HOST_PASSWORD and, if needed, "
                    "GENIUZLAB_EMAIL_PORT) as environment variables. Until then, "
                    "password reset, verification and notification emails are only "
                    "written to the server log — no user will ever receive them."
                ),
                id="geniuzlab.E001",
            )
        )
    if EMAIL_HOST and not os.environ.get("GENIUZLAB_EMAIL_HOST_USER"):
        issues.append(
            _CheckWarning(
                "GENIUZLAB_EMAIL_HOST is set but GENIUZLAB_EMAIL_HOST_USER is empty.",
                hint="Most SMTP providers reject unauthenticated senders — set the username env var too.",
                id="geniuzlab.W001",
            )
        )
    return issues


# ---------------------------------------------------------------------------
# Payment providers — GeniuzLab Payments Foundation
# Real checkout is enabled once the relevant secret key is present. Until
# then, transactions are recorded as "pending" so the rest of the platform
# (receipts, history, wallet crediting) keeps working end-to-end.
# ---------------------------------------------------------------------------
PAYMENT_PROVIDERS = {
    "paystack": {
        "public_key": os.environ.get("PAYSTACK_PUBLIC_KEY", ""),
        "secret_key": os.environ.get("PAYSTACK_SECRET_KEY", ""),
    },
    "flutterwave": {
        "public_key": os.environ.get("FLUTTERWAVE_PUBLIC_KEY", ""),
        "secret_key": os.environ.get("FLUTTERWAVE_SECRET_KEY", ""),
    },
    "monnify": {
        "api_key": os.environ.get("MONNIFY_API_KEY", ""),
        "secret_key": os.environ.get("MONNIFY_SECRET_KEY", ""),
        "contract_code": os.environ.get("MONNIFY_CONTRACT_CODE", ""),
    },
}


# ---------------------------------------------------------------------------
# Manual payment (bank transfer) — used for Academy course enrollment while
# online payment gateways (Paystack/Flutterwave/Monnify above) are
# temporarily disabled. Override any of these via environment variables
# without touching code.
# ---------------------------------------------------------------------------
MANUAL_PAYMENT = {
    "bank_name": os.environ.get("MANUAL_PAYMENT_BANK_NAME", "OPay"),
    "account_name": os.environ.get("MANUAL_PAYMENT_ACCOUNT_NAME", "OTSAJE GENIUS PETER"),
    "account_number": os.environ.get("MANUAL_PAYMENT_ACCOUNT_NUMBER", "9138955730"),
}

# WhatsApp number students are redirected to after submitting a payment claim.
# Digits only, with country code, no leading + or 00 (wa.me format).
ADMIN_WHATSAPP_NUMBER = os.environ.get("ADMIN_WHATSAPP_NUMBER", "2349138955730")


# ---------------------------------------------------------------------------
# Feature flags
# ---------------------------------------------------------------------------
# VTU (GeniuzSubs: airtime, data, cable TV, electricity), wallet funding, and
# subscription checkout (which depends on wallet funding) are temporarily
# switched off on the public-facing app. This is a soft-disable only:
# - All apps stay in INSTALLED_APPS, all models/migrations are untouched,
#   and the DB schema is fully preserved.
# - Every gated view still exists and still runs its real logic; the gate
#   just short-circuits it (404 or a redirect) before that logic runs, so
#   flipping this back to True re-enables everything with no code changes.
# - Navigation, dashboard quick actions, and the assistant chatbot all read
#   this flag to hide the relevant links/buttons so no dead links are shown.
FEATURE_VTU_ENABLED = env_bool("FEATURE_VTU_ENABLED", False)

# ---------------------------------------------------------------------------
# GeniuzSubs VTU — powered by VTpass (https://vtpass.com/documentation/)
# Sandbox by default; set VTPASS_LIVE_MODE=true once you've gone live on
# VTpass's dashboard and swapped in live keys.
# ---------------------------------------------------------------------------
VTPASS = {
    "api_key": os.environ.get("VTPASS_API_KEY", ""),
    "secret_key": os.environ.get("VTPASS_SECRET_KEY", ""),
    "public_key": os.environ.get("VTPASS_PUBLIC_KEY", ""),
    "live_mode": env_bool("VTPASS_LIVE_MODE", False),
}


# ---------------------------------------------------------------------------
# Cookie & session security — applied in ALL environments (not just prod),
# since these have no downside for local development.
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 7 days
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
CSRF_COOKIE_HTTPONLY = False  # must stay False if any JS reads the CSRF cookie for AJAX
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"

# ---------------------------------------------------------------------------
# Production security hardening — only applied when DEBUG is off, so local
# development (DEBUG=True) is unaffected.
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_SSL_REDIRECT = env_bool("GENIUZLAB_SECURE_SSL_REDIRECT", True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'
    CSRF_TRUSTED_ORIGINS = [
        o.strip() for o in os.environ.get("GENIUZLAB_CSRF_TRUSTED_ORIGINS", "").split(",") if o.strip()
    ]
    if not CSRF_TRUSTED_ORIGINS:
        raise RuntimeError(
            "GENIUZLAB_CSRF_TRUSTED_ORIGINS must be set (e.g. https://geniuzlab.com) "
            "when GENIUZLAB_DEBUG is False."
        )


# ---------------------------------------------------------------------------
# Automation — daily notifications + AI chat assistant
# ---------------------------------------------------------------------------

# Celery (used by automation/tasks.py + geniuzlab/celery.py). Needs a running
# broker in production — Redis is the simplest option. Everything still works
# without Celery: use `python manage.py run_automation_scheduler` (no extra
# infra) or a system cron entry calling `send_daily_notifications` instead.
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True

# AI chat assistant. Without a key it runs entirely on built-in rule-based
# responses (still fully functional) — set this to enable real LLM replies.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "loggers": {
        "automation": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "academy": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
