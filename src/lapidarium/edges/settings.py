"""Django settings for the engine.

An instance configures everything through the environment; a Python settings
module of its own is only needed for values the environment cannot express.
"""

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

# src/lapidarium
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    ADMIN_URL=(str, "admin/"),
    ALLOWED_HOSTS=(list, ["localhost"]),
    CACHE_URL=(str, "locmemcache://"),
    DEFAULT_FROM_EMAIL=(str, "webmaster@localhost"),
    EMAIL_URL=(str, "consolemail://"),
    GS_BUCKET_NAME=(str, ""),
    GS_LOCATION=(str, ""),
    MAILCHIMP_API_KEY=(str, ""),
    MAILCHIMP_LIST_ID=(str, ""),
    NEWSLETTER_BACKEND=(str, "log"),
    PAGE_CACHE_SECONDS=(int, 600),
    PAGE_CACHE_URL=(str, "filecache:///tmp/lapidarium-pages"),
    DEBUG=(bool, False),
    ENV=(str, "production"),
    LANGUAGE_CODE=(str, "pl"),
    MEDIA_ROOT=(str, "media"),
    MEDIA_URL=(str, "/media/"),
    SECRET_KEY=str,
    SITE_NAME=(str, "lapidarium"),
    SITE_THEME=(str, "base"),
    SITE_THEME_DIRS=(list, []),
    STATIC_ROOT=(str, "staticfiles"),
    TIME_ZONE=(str, "Europe/Warsaw"),
)

ENV = env("ENV")
IS_PRODUCTION = ENV == "production"
DEBUG: bool = env("DEBUG")
SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS: list[str] = env("ALLOWED_HOSTS")

SITE_NAME: str = env("SITE_NAME")

# Themes: the engine ships `base`, always loaded first; an
# instance adds its own directories, searched before the engine's.
ENGINE_THEMES = BASE_DIR / "themes"
ENGINE_TEMPLATES: Path = BASE_DIR / "templates"
SITE_THEME: str = env("SITE_THEME")


def _theme_dir(name: str) -> Path:
    for root in (*(Path(d) for d in env("SITE_THEME_DIRS")), ENGINE_THEMES):
        if (root / name / "tokens.css").is_file():
            return root / name
    msg = f"SITE_THEME {name!r}: no theme directory with a tokens.css."
    raise ImproperlyConfigured(msg)


# Each layer loads over the one before; a site theme named `base` replaces the
# engine's.
THEME_LAYERS: tuple[Path, ...] = tuple(
    {d.name: d for d in (ENGINE_THEMES / "base", _theme_dir(SITE_THEME))}.values()
)
ADMIN_URL = env("ADMIN_URL")

INSTALLED_APPS = [
    "unfold",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "lapidarium.links.db.django.apps.DbConfig",
    "lapidarium.gates.web.django.apps.WebGatesConfig",
    "lapidarium.gates.cli.django.apps.CliGatesConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise serves the collected STATIC_ROOT; outside production the dev
    # server serves from finders and tests do not fetch static files at all.
    *(["whitenoise.middleware.WhiteNoiseMiddleware"] if IS_PRODUCTION else []),
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "lapidarium.inits.ServiceInjectionMiddleware",
]

ROOT_URLCONF = "lapidarium.gates.web.django.urls"
# Management commands build their services here; web requests get them from
# the middleware.
SERVICES_FACTORY = "lapidarium.inits.Services"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Later layers override earlier ones and the engine, file by file.
        "DIRS": [*(d / "templates" for d in reversed(THEME_LAYERS)), ENGINE_TEMPLATES],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "lapidarium.gates.web.django.rendering.theme_stylesheets",
            ],
            "debug": DEBUG or ENV == "test",
        },
    }
]

WSGI_APPLICATION = "lapidarium.edges.wsgi.application"

DATABASES = {
    "default": {
        **env.db("DATABASE_URL"),
        "ATOMIC_REQUESTS": True,
        "CONN_MAX_AGE": 600,
        "CONN_HEALTH_CHECKS": True,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        )
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = env("LANGUAGE_CODE")
LANGUAGES = [("pl", "Polski"), ("en", "English")]
TIME_ZONE = env("TIME_ZONE")
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

STATIC_URL = "/static/"
STATIC_ROOT = env("STATIC_ROOT")
STATICFILES_DIRS = [
    BASE_DIR / "static",
    *((f"themes/{d.name}", d) for d in THEME_LAYERS),
]
MEDIA_URL = env("MEDIA_URL")
MEDIA_ROOT = env("MEDIA_ROOT")

GS_BUCKET_NAME = env("GS_BUCKET_NAME")
GS_LOCATION = env("GS_LOCATION")

# Media goes to GCS when a bucket is named, the filesystem otherwise. The client
# finds credentials itself (GOOGLE_APPLICATION_CREDENTIALS, or the attached
# service account on GCP). The bucket serves objects publicly, so URLs carry no
# signature.
STORAGES = {
    "default": (
        {
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
            "OPTIONS": {
                "bucket_name": GS_BUCKET_NAME,
                "location": GS_LOCATION,
                "default_acl": None,
                "querystring_auth": False,
            },
        }
        if GS_BUCKET_NAME
        else {"BACKEND": "django.core.files.storage.FileSystemStorage"}
    ),
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if IS_PRODUCTION
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# "pages" holds rendered public pages and is cleared on every content commit,
# so it must be shared by all workers: the default is a directory, not memory.
CACHES = {"default": env.cache("CACHE_URL"), "pages": env.cache("PAGE_CACHE_URL")}
PAGE_CACHE_SECONDS: int = env("PAGE_CACHE_SECONDS")

_EMAIL = env.email_url("EMAIL_URL")
_SMTP_OPTIONS = {
    "host": "EMAIL_HOST",
    "port": "EMAIL_PORT",
    "username": "EMAIL_HOST_USER",
    "password": "EMAIL_HOST_PASSWORD",
    "use_tls": "EMAIL_USE_TLS",
    "use_ssl": "EMAIL_USE_SSL",
}
# Only the SMTP backend takes connection options; the others reject them.
MAILERS = {
    "default": {
        "BACKEND": _EMAIL["EMAIL_BACKEND"],
        "OPTIONS": (
            {key: _EMAIL[name] for key, name in _SMTP_OPTIONS.items() if name in _EMAIL}
            if _EMAIL["EMAIL_BACKEND"].endswith(".smtp.EmailBackend")
            else {}
        ),
    }
}
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL")

# "log" or "mailchimp".
NEWSLETTER_BACKEND: str = env("NEWSLETTER_BACKEND")
MAILCHIMP_API_KEY: str = env("MAILCHIMP_API_KEY")
MAILCHIMP_LIST_ID: str = env("MAILCHIMP_LIST_ID")

UNFOLD = {
    "SITE_TITLE": SITE_NAME,
    "SITE_HEADER": SITE_NAME,
    "SITE_SYMBOL": "museum",
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
        "navigation": "lapidarium.links.db.django.admin.sidebar_navigation",
    },
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}

# Proxies in front that append to X-Forwarded-For; 0 trusts the header not at all.
TRUSTED_PROXY_HOPS: int = env.int(
    "TRUSTED_PROXY_HOPS", default=1 if IS_PRODUCTION else 0
)

if IS_PRODUCTION:
    SECURE_SSL_REDIRECT = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    USE_X_FORWARDED_HOST = True
    SECURE_REDIRECT_EXEMPT = [r"^healthz/"]
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
    X_FRAME_OPTIONS = "DENY"
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SECURE = True
    CSRF_COOKIE_SAMESITE = "Lax"
    CSRF_TRUSTED_ORIGINS = [
        f"https://{host.removeprefix('.')}" for host in ALLOWED_HOSTS
    ] + [f"https://*.{host[1:]}" for host in ALLOWED_HOSTS if host.startswith(".")]
