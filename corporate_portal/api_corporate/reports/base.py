"""Shared helpers for corporate report extraction.

Reports in this package query base tables directly (no stored procedures,
no views) on the `company_external` DB connection and return plain Python
lists/dicts ready for DRF JSON serialization.
"""
import datetime
from contextlib import contextmanager
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.db import connections


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class ReportError(Exception):
    """Raised by report fetchers to signal a clean, user-facing error.

    The dispatcher view catches this and returns an HTTP response with
    `self.status` and `self.message`.
    """

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.message = message
        self.status = status


# ---------------------------------------------------------------------------
# Cursor / row helpers
# ---------------------------------------------------------------------------

@contextmanager
def readonly_cursor(using: str = "company_external"):
    """Yield a read-only DB cursor on the external company DB.

    Usage::

        with readonly_cursor() as cur:
            cur.execute(sql, params)
            rows = dictfetchall(cur)
    """
    # Django closes the cursor automatically on context exit.
    with connections[using].cursor() as cur:
        yield cur


def dictfetchall(cursor) -> List[Dict[str, Any]]:
    """Return all rows from a cursor as a list of dicts keyed by column name.

    Uses ``cursor.description`` to obtain column names so it works for any
    SELECT (or any statement producing a result set).
    """
    cols = [c[0] for c in cursor.description]
    return [dict(zip(cols, row)) for row in cursor.fetchall()]


def sanitize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize a fetched row for JSON serialization.

    - ``date``/``datetime`` → ISO ``YYYY-MM-DD`` string (time portion dropped).
      The SQL ``CAST(... AS date)`` usually does this already, but this is a
      safety net for columns we forgot to cast.
    - ``Decimal`` is passed through unchanged. DRF's JSONRenderer serializes
      Decimal as a string, preserving precision for money columns.
    - Everything else (int, str, bool, None) is returned unchanged.
    """
    out: Dict[str, Any] = {}
    for k, v in row.items():
        if v is None:
            out[k] = None
        elif isinstance(v, datetime.date):  # also matches datetime.datetime
            out[k] = v.isoformat()[:10]
        elif isinstance(v, Decimal):
            out[k] = v
        else:
            out[k] = v
    return out


def parse_iso_date(value: Any, field_name: str = "date") -> datetime.date:
    """Parse a ``YYYY-MM-DD`` string into a ``date``.

    Raises ``ReportError`` (HTTP 400) on missing/invalid input. Returning a
    real ``date`` object (instead of a string) means the driver sends a
    typed parameter to SQL Server — no implicit string→date conversion.
    """
    if value is None or value == "":
        raise ReportError(f"{field_name} is required", status=400)
    if isinstance(value, datetime.date):
        return value
    try:
        return datetime.date.fromisoformat(value)
    except (ValueError, TypeError):
        raise ReportError(
            f"{field_name} must be in YYYY-MM-DD format, got: {value!r}",
            status=400,
        )