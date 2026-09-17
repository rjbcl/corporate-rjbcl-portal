"""Dashboard Data.

Python equivalent of ``proc_copo_dashboard_data``, returning three datasets:
latest policies, summary, and FUP data.

Returns a dict (not a list) with keys: latest_policies, summary, fup_data.
The view wraps this with company_id and group_ids metadata.

Notes
-----
- Three separate SQL queries replace the SP's three result sets.
- ``WITH (NOLOCK)`` preserved on all table references, matching the SP.
- Column names preserve the SP's case: ``policyNo``, ``sumassured``,
  ``premium``, ``maturitydate``, ``fup``, ``DaysUntilFUP``,
  ``totalPolicies``, ``activePolicies``, ``totalPremium``.
- ``{placeholders}`` interpolated in Python from validated group_ids list
  (only ``%s`` chars inserted, no user data).
- Dates as ISO ``YYYY-MM-DD``; money as ``Decimal``.
"""
from typing import Any, Dict, List

from .base import dictfetchall, readonly_cursor, sanitize_row


SQL_LATEST = """
SELECT TOP 10
    ed.PolicyNo                           AS policyNo,
    COALESCE(ge.Name, ge.NepName)         AS Name,
    SUM(ISNULL(ed.SumAssured, 0))         AS sumassured,
    SUM(ISNULL(ed.Premium, 0))            AS premium,
    CAST(MIN(ed.DOC) AS date)             AS DOC,
    CAST(MAX(ed.MaturityDate) AS date)    AS maturitydate
FROM    tblGroupEndowmentDetails ed WITH (NOLOCK)
        LEFT JOIN tblGroupEndowment ge WITH (NOLOCK)
            ON  ed.PolicyNo   = ge.PolicyNo
            AND ed.RegisterNo = ge.RegisterNo
WHERE   ed.SumAssured  > 0
  AND   ed.Premium     > 0
  AND   ed.PolicyStatus = 'A'
  AND   ed.GroupId IN ({placeholders})
GROUP BY ed.PolicyNo, COALESCE(ge.Name, ge.NepName)
ORDER BY MIN(ed.DOC) DESC;
"""


SQL_SUMMARY = """
SELECT
    COUNT(DISTINCT ed.PolicyNo)                                          AS totalPolicies,
    COUNT(DISTINCT CASE WHEN ed.PolicyStatus = 'A' THEN ed.PolicyNo END) AS activePolicies,
    SUM(CASE WHEN ed.PolicyStatus = 'A' THEN ed.Premium ELSE 0 END)      AS totalPremium
FROM    tblGroupEndowmentDetails ed WITH (NOLOCK)
WHERE   ed.GroupId IN ({placeholders});
"""


SQL_FUP = """
SELECT TOP 10
    ed.PolicyNo                           AS policyNo,
    COALESCE(ge.Name, ge.NepName)         AS Name,
    CAST(ed.FUP AS date)                  AS fup,
    DATEDIFF(DAY, GETDATE(), ed.FUP)      AS DaysUntilFUP
FROM    tblGroupEndowmentDetails ed WITH (NOLOCK)
        LEFT JOIN tblGroupEndowment ge WITH (NOLOCK)
            ON  ed.PolicyNo   = ge.PolicyNo
            AND ed.RegisterNo = ge.RegisterNo
WHERE   ed.GroupId IN ({placeholders})
ORDER BY ed.FUP DESC;
"""


def fetch(group_ids: List[str]) -> Dict[str, Any]:
    """Return dashboard data for the given group IDs.

    Returns a dict with keys:
        - ``latest_policies``: List[Dict] — top 10 by DOC DESC
        - ``summary``: Dict — totalPolicies, activePolicies, totalPremium
        - ``fup_data``: List[Dict] — top 10 by FUP DESC
    """
    if not group_ids:
        return {'latest_policies': [], 'summary': {}, 'fup_data': []}

    placeholders = ",".join(["%s"] * len(group_ids))

    with readonly_cursor() as cur:
        cur.execute(SQL_LATEST.format(placeholders=placeholders), group_ids)
        latest = [sanitize_row(r) for r in dictfetchall(cur)]

        cur.execute(SQL_SUMMARY.format(placeholders=placeholders), group_ids)
        summary_rows = dictfetchall(cur)
        summary = sanitize_row(summary_rows[0]) if summary_rows else {}

        cur.execute(SQL_FUP.format(placeholders=placeholders), group_ids)
        fup = [sanitize_row(r) for r in dictfetchall(cur)]

    return {
        'latest_policies': latest,
        'summary': summary,
        'fup_data': fup,
    }