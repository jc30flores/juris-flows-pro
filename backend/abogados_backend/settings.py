import os
from urllib.parse import urlparse
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
DEBUG = True

ALLOWED_HOSTS = [
    "relite-facturador.relitegroup.com",
    "localhost",
    "127.0.0.1",
]

CSRF_TRUSTED_ORIGINS = [
    "https://relite-facturador.relitegroup.com",
    "http://localhost:9104",
]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "abogados_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "abogados_backend.wsgi.application"
ASGI_APPLICATION = "abogados_backend.asgi.application"

def _database_from_url(database_url: str) -> dict:
    parsed = urlparse(database_url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or ""),
    }


DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL:
    DATABASES = {"default": _database_from_url(DATABASE_URL)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("DB_NAME", "abogados"),
            "USER": os.getenv("DB_USER", "jarvis"),
            "PASSWORD": os.getenv("DB_PASSWORD", "diez2030"),
            "HOST": os.getenv("DB_HOST", "127.0.0.1"),
            "PORT": os.getenv("DB_PORT", "5432"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/El_Salvador"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8184",
    "http://localhost:9104",
    "https://relite-facturador.relitegroup.com",
]
REST_FRAMEWORK = {}

INTERNET_HEALTH_URL = os.getenv("INTERNET_HEALTH_URL", "https://www.google.com/generate_204")
API_HEALTH_URL = os.getenv("API_HEALTH_URL", "https://p12172402231026.cheros.dev/health")
CONNECTIVITY_CHECK_INTERVAL = int(os.getenv("CONNECTIVITY_CHECK_INTERVAL", "15"))
CONNECTIVITY_CHECK_TIMEOUT = int(os.getenv("CONNECTIVITY_CHECK_TIMEOUT", "5"))

PRICE_OVERRIDE_ACCESS_CODE = os.getenv("PRICE_OVERRIDE_ACCESS_CODE", "123")
PRICE_OVERRIDE_TOKEN_MAX_AGE_SECONDS = int(
    os.getenv("PRICE_OVERRIDE_TOKEN_MAX_AGE_SECONDS", "300")
)
