"""Django settings for the NEXORA Business Contact Management System.

All deployment-specific values are read from the ``.env`` file so that no
password or secret ever lives in source code.
"""

from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
import os
import sys

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env once. Real environment variables win over the file, which lets
# you do:  DB_ENGINE=sqlite python manage.py runserver
load_dotenv(BASE_DIR / ".env", override=False)


def env_bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).strip().lower() in {"1", "true", "yes", "on"}


SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "insecure-development-key-change-me")


def env_list(key: str, default: str = "") -> list[str]:
    return [item.strip() for item in os.getenv(key, default).split(",") if item.strip()]


# Vercel sets VERCEL=1 in its build and runtime environments.
_is_vercel = bool(os.getenv("VERCEL") or os.getenv("VERCEL_ENV"))

DEBUG = env_bool("DJANGO_DEBUG", not _is_vercel)

ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "127.0.0.1,localhost")
if _is_vercel:
    # Deployment URLs are generated per build, so accept them by pattern.
    for _host in (
        ".vercel.app",
        os.getenv("VERCEL_URL"),
        os.getenv("VERCEL_PROJECT_PRODUCTION_URL"),
    ):
        if _host and _host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(_host)

_LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]"}
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")
for _host in ALLOWED_HOSTS:
    if _host == "*":
        continue
    if _host in _LOCAL_HOSTS:
        _origin = f"http://{_host}"
    elif _host.startswith("."):
        _origin = f"https://*{_host}"
    else:
        _origin = f"https://{_host}"
    if _origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_origin)

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    # NEXORA apps
    "apps.accounts",
    "apps.contacts",
    "apps.interactions",
    "apps.followups",
    "apps.reports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "nexora.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "nexora.context_processors.nexora_context",
            ],
        },
    },
]

WSGI_APPLICATION = "nexora.wsgi.application"
ASGI_APPLICATION = "nexora.asgi.application"

# ---------------------------------------------------------------------------
# Database — MySQL by default, SQLite only for an instant offline demo
# ---------------------------------------------------------------------------
DB_ENGINE = os.getenv("DB_ENGINE", "mysql").strip().lower()


# Serverless functions should not hold a MySQL connection between invocations.
_db_conn_max_age = 0 if _is_vercel else 60


def _mysql_options(ssl: bool = False) -> dict:
    options = {
        "charset": "utf8mb4",
        "init_command": "SET sql_mode='STRICT_TRANS_TABLES'",
    }
    if ssl:
        # Enables TLS with the system CA bundle (required by most hosted MySQL).
        options["ssl"] = {}
    return options


def _mysql_from_url(url: str) -> dict:
    """Build a MySQL config from mysql://user:pass@host:port/name?ssl=true."""
    parsed = urlparse(url.replace("mysql2://", "mysql://", 1))
    query = parse_qs(parsed.query)
    ssl_flag = env_bool("DB_SSL", False) or any(
        query.get(key, [""])[0].lower()
        in {"1", "true", "required", "strict", "verify_ca", "verify_identity"}
        for key in ("ssl", "ssl-mode", "ssl_mode", "sslmode", "sslaccept")
    )
    return {
        "ENGINE": "django.db.backends.mysql",
        "NAME": parsed.path.lstrip("/") or os.getenv("DB_NAME", ""),
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "127.0.0.1",
        "PORT": str(parsed.port or 3306),
        "OPTIONS": _mysql_options(ssl_flag),
        "TEST": {"NAME": "test_nexora_db"},
        "CONN_MAX_AGE": _db_conn_max_age,
        "CONN_HEALTH_CHECKS": True,
    }


def _postgres_from_url(url: str) -> dict:
    """Build a PostgreSQL config from postgres://user:pass@host:port/name.

    Used only when a Vercel Marketplace database integration injects a
    PostgreSQL URL (DATABASE_URL / POSTGRES_URL). MySQL stays the default.
    """
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    options: dict = {}
    sslmode = (query.get("sslmode") or [""])[0]
    if sslmode:
        options["sslmode"] = sslmode
    elif (parsed.hostname or "").endswith((".neon.tech", ".supabase.co", ".render.com")):
        # These providers refuse plain-text connections.
        options["sslmode"] = "require"
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/") or "postgres",
        "USER": unquote(parsed.username or ""),
        "PASSWORD": unquote(parsed.password or ""),
        "HOST": parsed.hostname or "127.0.0.1",
        "PORT": str(parsed.port or 5432),
        "OPTIONS": options,
        "CONN_MAX_AGE": _db_conn_max_age,
        "CONN_HEALTH_CHECKS": True,
    }


# A hosted provider can be configured with a single connection URL.
_mysql_url = (os.getenv("MYSQL_URL") or os.getenv("DATABASE_URL") or "").strip()
_postgres_url = (os.getenv("POSTGRES_URL") or "").strip()
if not _postgres_url and _mysql_url.startswith(("postgres://", "postgresql://")):
    _postgres_url = _mysql_url

if DB_ENGINE == "sqlite":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / os.getenv("SQLITE_NAME", "db.sqlite3"),
        }
    }
elif _mysql_url.startswith(("mysql://", "mysql2://", "mariadb://")):
    DATABASES = {"default": _mysql_from_url(_mysql_url)}
elif _postgres_url.startswith(("postgres://", "postgresql://")):
    DATABASES = {"default": _postgres_from_url(_postgres_url)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("DB_NAME", "nexora_db"),
            "USER": os.getenv("DB_USER", "root"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "3306"),
            "OPTIONS": _mysql_options(env_bool("DB_SSL", False)),
            "TEST": {"NAME": "test_nexora_db"},
            "CONN_MAX_AGE": _db_conn_max_age,
            "CONN_HEALTH_CHECKS": True,
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["apps.accounts.backends.UsernameOrEmailBackend"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Tests create many accounts; PBKDF2 would dominate the run time.
if "test" in sys.argv:
    PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dashboard"
LOGOUT_REDIRECT_URL = "accounts:login"

SESSION_COOKIE_AGE = 60 * 60 * 8          # 8 hours
SESSION_EXPIRE_AT_BROWSER_CLOSE = True    # unless "Remember me" is ticked
SESSION_SAVE_EVERY_REQUEST = True

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("DJANGO_TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

DATE_INPUT_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]
DATETIME_INPUT_FORMATS = [
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M",
]

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

# ---------------------------------------------------------------------------
# Security & messaging
# ---------------------------------------------------------------------------
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
# Vercel (and any reverse proxy) terminates TLS and forwards this header.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# NEXORA product metadata (shown in the UI)
NEXORA = {
    "NAME": "NEXORA",
    "TAGLINE": "Smart Connections. Smarter Management.",
    "VERSION": "1.0.0",
}
