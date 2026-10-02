"""Django settings for the engine.

An instance configures everything through the environment; a Python settings
module of its own is only needed for values the environment cannot express.
"""

from pathlib import Path

import environ

# src/lapidarium
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    ADMIN_URL=(str, "admin/"),
    ALLOWED_HOSTS=(list, ["localhost"]),
    AWS_STORAGE_BUCKET_NAME=(str, ""),
    DEBUG=(bool, False),
    ENV=(str, "production"),
    LANGUAGE_CODE=(str, "pl"),
    MEDIA_ROOT=(str, "media"),
    MEDIA_URL=(str, "/media/"),
    SECRET_KEY=str,
    SITE_NAME=(str, "lapidarium"),
    STATIC_ROOT=(str, "staticfiles"),
    TIME_ZONE=(str, "Europe/Warsaw"),
)

ENV = env("ENV")
IS_PRODUCTION = ENV == "production"
DEBUG = env("DEBUG")
SECRET_KEY = env("SECRET_KEY")
ALLOWED_HOSTS: list[str] = env("ALLOWED_HOSTS")

SITE_NAME = env("SITE_NAME")
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
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
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
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = env("MEDIA_URL")
MEDIA_ROOT = env("MEDIA_ROOT")

AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
# The S3 backend reads AWS_* from the environment itself; the bucket name is
# the switch that turns it on.
STORAGES = {
    "default": {
        "BACKEND": (
            "storages.backends.s3.S3Storage"
            if AWS_STORAGE_BUCKET_NAME
            else "django.core.files.storage.FileSystemStorage"
        )
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if IS_PRODUCTION
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

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
