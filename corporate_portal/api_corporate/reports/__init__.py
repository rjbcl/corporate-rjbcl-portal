"""Corporate reports — direct-to-table extraction layer.

Each module here replaces a branch of `proc_copo_GroupReport` with a plain
parameterized SQL query against base tables. No stored procedures, no SQL
views.
"""
from .base import ReportError, readonly_cursor, dictfetchall, sanitize_row, parse_iso_date
from .registry import REPORTS

__all__ = [
    "ReportError",
    "readonly_cursor",
    "dictfetchall",
    "sanitize_row",
    "parse_iso_date",
    "REPORTS",
]