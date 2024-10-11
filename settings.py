import os
from pathlib import Path

import dj_database_url

from patch_environ import patch_environ

# Optionally patch the environment with file-based variables.
patch_environ(os.getenv("PATCH_ENVIRON_PATH"))


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-a94cjadrz=y0o+c75138ro=gn3oq0*by)gs1cs88k$9+taepp("

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    "debug_toolbar",
    "django.contrib.humanize",
    "django.contrib.staticfiles",
    "django_filters",
    "rest_framework",
    "crawler",
    "viewer",
]

MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

INTERNAL_IPS = [
    "127.0.0.1",
]

ROOT_URLCONF = "urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "viewer/static/icons"],
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "viewer.context_processors.crawl_stats",
            ],
            "loaders": [
                (
                    "django.template.loaders.cached.Loader",
                    [
                        "django.template.loaders.filesystem.Loader",
                        "django.template.loaders.app_directories.Loader",
                        "viewer.loaders.IgnoreMissingSVGsTemplateLoader",
                    ],
                ),
            ],
        },
    },
]

WSGI_APPLICATION = "wsgi.application"


# The default database is configured to use a sample SQLite file.
# Override this by setting DATABASE_URL in the environment.
# See https://github.com/jazzband/dj-database-url for URL formatting.
_sample_db_path = f"{BASE_DIR}/sample/sample.sqlite3"

DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{_sample_db_path}",
    ),
}

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "America/New_York"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = "static/"

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

ALLOWED_HOSTS = ["*"]

# django-debug-toolbar
DEBUG_TOOLBAR_CONFIG = {
    "SHOW_COLLAPSED": True,
}

# django-rest-framework
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_PAGINATION_CLASS": "viewer.pagination.BetterPageNumberPagination",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
        "rest_framework_csv.renderers.CSVStreamingRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "PAGE_SIZE": 25,
    "UNAUTHENTICATED_USER": None,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": " %(asctime)s.%(msecs)03d %(levelname)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "loggers": {
        "crawler": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}

GOOGLE_TAG_ID = os.getenv("GOOGLE_TAG_ID")
