"""Maturity Forecasting Report.

Python equivalent of ``proc_copo_GroupReport @Flag='MaturityForecastingReport'``,
querying the base tables ``tblGroupEndowment`` and ``tblGroupEndowmentDetails``
directly instead of the deprecated ``view_copo_groupEndowment`` view.

Join semantics mirror the view exactly::

    tblGroupEndowment ge
    INNER JOIN tblGroupEndowmentDetails ged
        ON  ge.RegisterNo = ged.RegisterNo
        AND ge.PolicyNo   = ged.PolicyNo
"""
from typing import Any, Dict, List

from .base import (
    dictfetchall,
    parse_iso_date,
    readonly_cursor,
    sanitize_row,
)


SQL = """
SELECT  ROW_NUMBER() OVER (ORDER BY ged.PolicyNo) AS SN,
        ged.PolicyNo,
        ge.Branch,
        ge.Name,
        ge.NepName,
        ged.GroupId,
        CAST(ge.DOB AS date)                        AS DOB,
        CAST(MIN(ged.DOC) AS date)                  AS DOC,
        SUM(ged.SumAssured)                         AS SumAssured,
        MAX(ged.Term)                               AS Term,
        MAX(ged.Instalment)                         AS Instalment,
        SUM(ged.Premium)                            AS Premium,
        CAST(ged.MaturityDate AS date)              AS MaturityDate,
        COUNT(ged.PolicyNo)                         AS TotalPolicy,
        DATEDIFF(DAY, GETDATE(), ged.MaturityDate)  AS RemainingDayToMature,
        ged.PolicyStatus
FROM    tblGroupEndowment ge
        INNER JOIN tblGroupEndowmentDetails ged
            ON  ge.RegisterNo = ged.RegisterNo
            AND ge.PolicyNo   = ged.PolicyNo
WHERE   ged.GroupId      = %s
  AND   ged.PolicyStatus = 'A'
  AND   ged.PolicyNo IS NOT NULL
  AND   CAST(ged.MaturityDate AS date) BETWEEN %s AND %s
GROUP BY ged.PolicyNo, ge.Branch, ge.Name, ge.NepName,
         ged.GroupId, ge.DOB, ged.MaturityDate, ged.PolicyStatus
ORDER BY ged.PolicyNo;
"""


def fetch(group_id: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
    """Return the maturity forecasting report rows for the given group & range.

    Args:
        group_id: e.g. ``'GE1001'``
        from_date: ISO date string ``'YYYY-MM-DD'``
        to_date:   ISO date string ``'YYYY-MM-DD'``

    Returns:
        List of dicts with keys: ``SN, PolicyNo, Branch, Name, NepName,
        GroupId, DOB, DOC, SumAssured, Term, Instalment, Premium,
        MaturityDate, TotalPolicy, RemainingDayToMature, PolicyStatus``.
    """
    fd = parse_iso_date(from_date, "from_date")
    td = parse_iso_date(to_date,   "to_date")
    if fd > td:
        from .base import ReportError
        raise ReportError("from_date cannot be after to_date", status=400)

    with readonly_cursor() as cur:
        cur.execute(SQL, [group_id, fd, td])
        rows = dictfetchall(cur)

    return [sanitize_row(r) for r in rows]