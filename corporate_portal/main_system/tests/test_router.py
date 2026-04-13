"""
Test-time database router.

Prevents Django's test runner from trying to create / migrate the
`company_external` MSSQL database, which is not available in the
test environment.  All models that live there are `managed = False`
(GroupInformation, GroupEndowment in api_corporate) so they need no
table creation anyway.

Usage — add to settings.py (or a test-specific settings override):

    DATABASE_ROUTERS = ['main_system.tests.test_router.TestRouter']

Or pass it on the command line:

    python manage.py test --settings=corporate_portal.test_settings
"""


class TestRouter:
    """
    Routes every database operation to `default` (PostgreSQL).
    Completely blocks any interaction with `company_external` so the
    MSSQL driver is never invoked during tests.
    """

    EXCLUDED_DB = "company_external"

    # ── Read ──────────────────────────────────────────────────────────────────

    def db_for_read(self, model, **hints):
        """All reads go to default."""
        return "default"

    # ── Write ─────────────────────────────────────────────────────────────────

    def db_for_write(self, model, **hints):
        """All writes go to default."""
        return "default"

    # ── Relations ─────────────────────────────────────────────────────────────

    def allow_relation(self, obj1, obj2, **hints):
        """Allow relations between any two objects in the default DB."""
        return True

    # ── Migrations ────────────────────────────────────────────────────────────

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Only run migrations on `default`.
        Returning False for company_external prevents the test runner
        from even attempting a connection to the MSSQL server.
        """
        if db == self.EXCLUDED_DB:
            return False
        return True