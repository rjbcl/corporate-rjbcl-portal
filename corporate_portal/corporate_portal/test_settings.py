"""
corporate_portal/test_settings.py
===================================
Minimal settings override for running the test suite.

Usage:
    python manage.py test --settings=corporate_portal.test_settings

"""

from corporate_portal.settings import *  # noqa: F401, F403

# 1. Test-time database router
DATABASE_ROUTERS = ["main_system.tests.test_router.TestRouter"]

# 2. Fast SQLite DB for default (remove if you want real Postgres in CI)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },

    "company_external": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    },
}

# 3. Silence password hashing to speed up tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# 4. Disable caching side-effects in tests
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.dummy.DummyCache",
    }
}