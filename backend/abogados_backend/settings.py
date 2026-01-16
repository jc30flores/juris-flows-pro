import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv("SECRET_KEY", "changeme")
DEBUG = os.getenv("DEBUG", "True").strip().lower() == "true"

ALLOWED_HOSTS = [
    "zelaya-sport.cuskatech.com",
    "localhost",
    "127.0.0.1",
]

if DEBUG:
    print("[ENV] DTE_API_BASE_URL loaded:", bool(os.getenv("DTE_API_BASE_URL")))

CSRF_TRUSTED_ORIGINS = [
    "https://zelaya-sport.cuskatech.com",
    "http://localhost:9007",
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

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "zelayasdb"),
        "USER": os.getenv("DB_USER", "jarvis"),
        "PASSWORD": os.getenv("DB_PASSWORD", "diez2030"),
        "HOST": os.getenv("DB_HOST", "localhost"),
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
    "http://localhost:8185",
    "http://localhost:9007",
    "https://zelaya-sport.cuskatech.com",
]
REST_FRAMEWORK = {}

INTERNET_HEALTH_URL = os.getenv("INTERNET_HEALTH_URL", "https://www.google.com/generate_204")
API_HEALTH_URL = os.getenv("API_HEALTH_URL", "https://t12152606851014.cheros.dev/health")
CONNECTIVITY_CHECK_INTERVAL = int(os.getenv("CONNECTIVITY_CHECK_INTERVAL", "15"))
CONNECTIVITY_CHECK_TIMEOUT = int(os.getenv("CONNECTIVITY_CHECK_TIMEOUT", "5"))
CONNECTIVITY_SENTINEL_ENABLED = os.getenv("CONNECTIVITY_SENTINEL_ENABLED", "1") == "1"
DTE_AUTORETRY_BACKOFF_SECONDS = int(os.getenv("DTE_AUTORETRY_BACKOFF_SECONDS", "60"))
DTE_AUTORETRY_BATCH_SIZE = int(os.getenv("DTE_AUTORETRY_BATCH_SIZE", "25"))
DTE_API_BASE_URL = os.getenv("DTE_API_BASE_URL", "").strip()
DTE_API_INVALIDACION_URL = os.getenv("DTE_API_INVALIDACION_URL", "").strip()
DTE_API_TOKEN = os.getenv("DTE_API_TOKEN", "").strip()
DTE_FACTURA_URL = os.getenv("DTE_FACTURA_URL", "").strip()
DTE_ENDPOINT_FACTURA = os.getenv("DTE_ENDPOINT_FACTURA", "").strip()
DTE_INVALIDATION_CONNECT_TIMEOUT = int(os.getenv("DTE_INVALIDATION_CONNECT_TIMEOUT", "5"))
DTE_INVALIDATION_READ_TIMEOUT = int(os.getenv("DTE_INVALIDATION_READ_TIMEOUT", "25"))
DTE_INVALIDATION_VERIFY_SSL = (
    os.getenv("DTE_INVALIDATION_VERIFY_SSL", "true").strip().lower() == "true"
)
CONNECTIVITY_CHECK_URL = os.getenv("CONNECTIVITY_CHECK_URL", "").strip()

PRICE_OVERRIDE_ACCESS_CODE = os.getenv("PRICE_OVERRIDE_ACCESS_CODE", "123")
