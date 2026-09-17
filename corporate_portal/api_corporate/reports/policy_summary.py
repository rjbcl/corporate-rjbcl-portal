"""Policy Summary Report.

Python equivalent of querying ``view_copo_policySummary``, inlined against
base tables. Single-policy lookup filtered by the user's authorized groups.

Tables
------
- ``tblGroupEndowment`` (a) — policy holder info
- ``tblGroupEndowmentDetails`` (b) — premium / SA / instalment info
- ``tblStaticDataValue`` (s) — LEFT JOIN for Occupation lookup
  (TRY_CAST(a.Occupation AS INT) = s.Id; falls back to raw Occupation if no match)

Notes
-----
- Output column case preserves the original view's quirks:
    * ``Sumassured``     (lowercase 'a' in 'assured')
    * ``maturitydate``   (all lowercase)
  These are aliased explicitly to keep the shape identical.
- Dates as ISO ``YYYY-MM-DD``; money as ``Decimal``.
- No NOLOCK (view didn't use it).
- Response is a BARE ARRAY (no envelope).
- ``{placeholders}`` is interpolated in Python from the validated
  ``group_ids`` list — only ``%s`` chars are inserted, no user data.
"""
from typing import Any, Dict, List

from .base import (
    ReportError,
    dictfetchall,
    readonly_cursor,
    sanitize_row,
)


SQL_TEMPLATE = """
SELECT  a.PolicyNo,
        a.Branch,
        a.Name,
        a.NepName,
        a.GroupId,
        CAST(a.DOB AS date)            AS DOB,
        a.Gender,
        a.Address,
        a.Email,
        a.Mobile,
        a.FatherName,
        a.MotherName,
        a.NomineeName,
        a.NomineeRelationship,
        CAST(a.ClaimDate AS date)     AS ClaimDate,
        a.DistrictID,
        a.WardNo,
        a.NomineePhone,
        a.NomineeAddress,
        COALESCE(s.Value, a.Occupation) AS Occupation,
        b.SumAssured                   AS Sumassured,
        CAST(b.DOC AS date)           AS DOC,
        CAST(b.PaidDate AS date)       AS PaidDate,
        CAST(b.FUP AS date)            AS FUP,
        b.Term,
        b.Premium,
        b.Instalment,
        b.PaidAmount,
        CAST(b.MaturityDate AS date)  AS maturitydate,
        b.PolicyStatus,
        b.PolicyType
FROM    tblGroupEndowment AS a
        INNER JOIN tblGroupEndowmentDetails AS b
            ON  a.PolicyNo   = b.PolicyNo
            AND a.RegisterNo = b.RegisterNo
        LEFT JOIN tblStaticDataValue AS s
            ON TRY_CAST(a.Occupation AS INT) = s.Id
WHERE   a.PolicyNo = %s
  AND   a.GroupId IN ({placeholders});
"""


def fetch(policy_no: str, group_ids: List[str]) -> List[Dict[str, Any]]:
    """Return policy summary rows for a single policy, restricted to the
    user's authorized group_ids.

    Args:
        policy_no: e.g. 'GE1001-001'
        group_ids: list of GroupId strings the user is allowed to see.
            If empty, returns an empty list (no rows).

    Returns:
        List of dicts with keys matching ``view_copo_policySummary`` columns.
    """
    if not policy_no:
        raise ReportError("policy_no is required", status=400)
    if not group_ids:
        return []

    # Only %s placeholders are interpolated; the actual group_ids go through
    # the parameterized execute() call. Safe from SQL injection.
    placeholders = ",".join(["%s"] * len(group_ids))
    sql = SQL_TEMPLATE.format(placeholders=placeholders)

    with readonly_cursor() as cur:
        cur.execute(sql, [policy_no, *group_ids])
        rows = dictfetchall(cur)

    return [sanitize_row(r) for r in rows]