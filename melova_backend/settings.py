"""
Django settings for melova_backend project.
"""

from datetime import timedelta
from pathlib import Path

import dotenv
import os

# Load .env file
dotenv.load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "django-insecure-43x+ins+@l4!&3=(&e1^s^e777l69hqig!wv8oo67#gu9zn934",
)
DEBUG = os.environ.get("DEBUG", "True") == "True"
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",") if os.environ.get("ALLOWED_HOSTS") else ["*"]


# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "social_django",
    # Local apps
    "accounts",
    "shop",
    "payments",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",          # must be very first
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "social_django.middleware.SocialAuthExceptionMiddleware",
]

ROOT_URLCONF = "melova_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "social_django.context_processors.backends",
                "social_django.context_processors.login_redirect",
            ],
        },
    },
]

WSGI_APPLICATION = "melova_backend.wsgi.application"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ---------------------------------------------------------------------------
# Custom User Model
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"


# ---------------------------------------------------------------------------
# Authentication Backends
# ---------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    "social_core.backends.google.GoogleOAuth2",
    "django.contrib.auth.backends.ModelBackend",
]


# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
}


# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}


# ---------------------------------------------------------------------------
# Google OAuth2
# ---------------------------------------------------------------------------
SOCIAL_AUTH_GOOGLE_OAUTH2_KEY = os.environ.get("GOOGLE_CLIENT_ID", "")
SOCIAL_AUTH_GOOGLE_OAUTH2_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]
# Tell social-auth to use our custom User model
SOCIAL_AUTH_USER_MODEL = "accounts.User"


# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOW_ALL_ORIGINS = DEBUG  # allow all in dev; restrict in production
CORS_ALLOWED_ORIGINS = os.environ.get("CORS_ALLOWED_ORIGINS", "http://localhost:3000").split(",")


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Razorpay Settings
# ---------------------------------------------------------------------------
RAZOR_KEY_ID = os.environ.get("RAZOR_KEY_ID")
RAZOR_KEY_SECRET = os.environ.get("RAZOR_KEY_SECRET")

# ---------------------------------------------------------------------------
# Media files (Local Storage)
# ---------------------------------------------------------------------------
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"