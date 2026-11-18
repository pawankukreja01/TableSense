import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SECRET_KEY = os.environ.get("SECRET_KEY", "local-development-only")
PRODUCTION = os.environ.get("PRODUCTION") == "1"
if PRODUCTION and len(SECRET_KEY) < 40:
    raise RuntimeError("Set a unique SECRET_KEY of at least 40 characters")
DEBUG = not PRODUCTION
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",")
ROOT_URLCONF = "server.urls"
WSGI_APPLICATION = "server.wsgi.application"
INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "rest_framework",
    "pilot",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": os.getenv("SQLITE_PATH", str(BASE_DIR / "pilot.sqlite3")),
        "OPTIONS": {"timeout": 20},
    }
}
if os.getenv("POSTGRES_HOST"):
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "tablesense",
        "USER": "tablesense",
        "HOST": os.environ["POSTGRES_HOST"],
        "PASSWORD": os.environ["POSTGRES_PASSWORD"],
    }
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
USE_TZ = True
TIME_ZONE = "Europe/London"
STATIC_URL = "/static/"
WHITENOISE_ROOT = BASE_DIR / "frontend/dist"
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = PRODUCTION
SESSION_COOKIE_SAMESITE = "Strict"
SECURE_CONTENT_TYPE_NOSNIFF = True
DEMO_MODE = not PRODUCTION and os.getenv("DEMO_MODE", "1") == "1"
REST_FRAMEWORK = {
    "UNAUTHENTICATED_USER": None,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication"
    ],
    "DEFAULT_THROTTLE_RATES": {"login": "12/min", "pair": "12/min"},
}
PROMOTIONS = os.getenv("ENABLE_PROMOTIONS", "0") == "1"
if os.getenv("TRUST_HTTPS_PROXY") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
