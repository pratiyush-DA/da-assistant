import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    EMBEDDING_DIMENSIONS=(int, 1024),
    RERANK_ENABLED=(bool, False),
    HYBRID_SEARCH_ENABLED=(bool, True),
    VECTOR_SEARCH_LIMIT=(int, 12),
    FULLTEXT_SEARCH_LIMIT=(int, 15),
    RRF_K=(int, 60),
    MULTI_HOP_ENABLED=(bool, True),
    LLM_MAX_COMPLETION_TOKENS=(int, 1024),
    LLM_MAX_REQUEST_TOKENS=(int, 5500),
    LLM_TEMPERATURE=(float, 0.7),
    PARENT_CHUNK_TOKENS=(int, 2000),
    CHILD_CHUNK_TOKENS=(int, 200),
)

environ.Env.read_env(os.path.join(BASE_DIR.parent, ".env"))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-insecure-change-me")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "api"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "apps.core",
    "apps.clients",
    "apps.documents",
    "apps.chat",
    "apps.users",
    "apps.conversations",
    "apps.lineage",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

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
            ],
        },
    },
]

DATABASES = {
    "default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"),
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
}

CORS_ALLOWED_ORIGINS = env.list(
    "CORS_ALLOWED_ORIGINS",
    default=["http://localhost:3000", "http://127.0.0.1:3000"],
)
CORS_ALLOW_CREDENTIALS = True

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60

NEO4J_URI = env("NEO4J_URI", default="bolt://localhost:7687")
NEO4J_USER = env("NEO4J_USER", default="neo4j")
NEO4J_PASSWORD = env("NEO4J_PASSWORD", default="password")
NEO4J_DATABASE = env("NEO4J_DATABASE", default="neo4j")

STORAGE_BACKEND = env("STORAGE_BACKEND", default="local")
MEDIA_ROOT = env("MEDIA_ROOT", default=str(BASE_DIR / "uploads"))

GROQ_API_KEY = env("GROQ_API_KEY", default="")
GROQ_MODEL = env("GROQ_MODEL", default="llama-3.1-8b-instant")
LLM_MAX_COMPLETION_TOKENS = env("LLM_MAX_COMPLETION_TOKENS")
# Groq on_demand llama-3.1-8b-instant TPM is 6000; keep total request under that.
LLM_MAX_REQUEST_TOKENS = env("LLM_MAX_REQUEST_TOKENS")
LLM_TEMPERATURE = env("LLM_TEMPERATURE")

EMBEDDING_MODEL = env("EMBEDDING_MODEL", default="BAAI/bge-large-en-v1.5")
EMBEDDING_DIMENSIONS = env("EMBEDDING_DIMENSIONS")
RERANK_ENABLED = env("RERANK_ENABLED")

PARENT_CHUNK_TOKENS = env("PARENT_CHUNK_TOKENS")
CHILD_CHUNK_TOKENS = env("CHILD_CHUNK_TOKENS")
VECTOR_SEARCH_LIMIT = env("VECTOR_SEARCH_LIMIT")
HYBRID_SEARCH_ENABLED = env("HYBRID_SEARCH_ENABLED")
FULLTEXT_SEARCH_LIMIT = env("FULLTEXT_SEARCH_LIMIT")
RRF_K = env("RRF_K")
MULTI_HOP_ENABLED = env("MULTI_HOP_ENABLED")
VECTOR_INDEX_NAME = "chunk_embeddings"
FULLTEXT_INDEX_NAME = "childChunkSearch"

AUTH_PLACEHOLDER = True
