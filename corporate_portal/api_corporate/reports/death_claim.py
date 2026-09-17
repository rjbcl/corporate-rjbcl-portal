"""Death Claim Report.

Python equivalent of ``proc_copo_GroupReport @Flag='GroupDeathReport'``,
querying base tables directly.

Join semantics (mirrors the SP)::

    tblGroupDeathClaim dc
    INNER JOIN (
        -- tempGroupEndowmentDeath: aggregated endowment rows for deceased policies
        SELECT PolicyNo, EmployeeId, GroupId, Name, NepName, DOB,
               MIN(DOC) AS DOC, SUM(Premium) AS Premium, SUM(SumAssured) AS SA,
               MaturityDate
        FROM tblGroupEndowment
        WHERE PolicyStatus = 'D' AND GroupId = ?
        GROUP BY EmployeeId, PolicyNo, GroupId, Name, NepName, DOB, MaturityDate
    ) ge  ON dc.PolicyNo = ge.PolicyNo
    INNER JOIN (
        -- tempGroupEndowmentDetails: max instalment per deceased policy
        SELECT PolicyNo, MAX(Instalment) AS Instalment
        FROM tblGroupEndowmentDetails
        WHERE PolicyStatus = 'D' AND GroupId = ?
        GROUP BY PolicyNo
    ) ged ON dc.PolicyNo = ged.PolicyNo

Filter:
    dc.PaidDate BETWEEN ? AND ?

Notes
-----
- ``@PolicyNo`` SP parameter dropped (was always NULL from Django).
- ``@FromDate``/``@ToDate`` ISNULL fallback dropped (Django always sends both).
- Redundant ``b.GroupId = @GroupId`` in outer WHERE dropped (already filtered
  inside the tempGroupEndowmentDeath subquery).
- ``Term`` no longer selected in the tempGroupEndowmentDeath subquery
  (was a dead column — CTE 3 never referenced ``b.Term``).
- No NOLOCK (SP didn't use it for this branch).
- Output has TWO similar columns:
    * ``ClaimAmount``      = raw ``dc.TotalClaimAmount`` (from claim table)
    * ``TotalClaimAmount``  = computed ``ge.SA + dc.TotalBonus``
  Both preserved as separate keys — easy to mis-alias.
- ``NetClaimAmount`` = ``ge.SA + dc.TotalBonus - LoanAmount - CalculatedInterest``
  with NULL coalesced to 0 for the loan/interest subtractions.
- Dates as ISO ``YYYY-MM-DD``; money as ``Decimal`` (DRF serializes as string).
- Response shape is a BARE ARRAY (no envelope) — matches existing view.
"""
from typing import Any, Dict, List

from .base import (
    ReportError,
    dictfetchall,
    parse_iso_date,
    readonly_cursor,
    sanitize_row,
)


SQL = """
SELECT  dc.GroupId,
        ge.PolicyNo,
        ge.EmployeeId,
        ge.Name,
        ge.NepName,
        CAST(ge.DOB AS date)                  AS DOB,
        ge.SA,
        ge.Premium,
        CAST(ge.DOC AS date)                  AS DOC,
        CAST(ge.MaturityDate AS date)         AS MaturityDate,
        dc.TotalBonus                         AS Bonus,
        dc.TotalClaimAmount                   AS ClaimAmount,
        dc.LoanAmount,
        dc.CalculatedInterest                 AS InterestOnLoanAmount,
        ge.SA + dc.TotalBonus                 AS TotalClaimAmount,
        ge.SA + dc.TotalBonus
            - ISNULL(dc.LoanAmount, 0)
            - ISNULL(dc.CalculatedInterest, 0) AS NetClaimAmount,
        CAST(dc.DeathDate AS date)            AS DeathDate,
        CAST(dc.IntimationDate AS date)       AS IntimationDate,
        CAST(dc.TerminationDate AS date)      AS TerminationDate,
        dc.VoucherNo,
        dc.ClaimId,
        ged.Instalment
FROM    tblGroupDeathClaim dc
        INNER JOIN (
            SELECT  PolicyNo, EmployeeId, GroupId, Name, NepName, DOB,
                    MIN(DOC)        AS DOC,
                    SUM(Premium)    AS Premium,
                    SUM(SumAssured) AS SA,
                    MaturityDate
            FROM    tblGroupEndowment
            WHERE   PolicyStatus = 'D'
              AND   GroupId = %s
            GROUP BY EmployeeId, PolicyNo, GroupId, Name, NepName, DOB, MaturityDate
        ) ge  ON dc.PolicyNo = ge.PolicyNo
        INNER JOIN (
            SELECT  PolicyNo, MAX(Instalment) AS Instalment
            FROM    tblGroupEndowmentDetails
            WHERE   PolicyStatus = 'D'
              AND   GroupId = %s
            GROUP BY PolicyNo
        ) ged ON dc.PolicyNo = ged.PolicyNo
WHERE   CAST(dc.PaidDate AS date) BETWEEN %s AND %s;
"""


def fetch(group_id: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
    """Return the death claim report rows for the given group & range.

    Args:
        group_id: e.g. ``'GE1001'``
        from_date: ISO date string ``'YYYY-MM-DD'`` (filter on dc.PaidDate)
        to_date:   ISO date string ``'YYYY-MM-DD'``

    Returns:
        List of dicts with keys: ``GroupId, PolicyNo, EmployeeId, Name,
        NepName, DOB, SA, Premium, DOC, MaturityDate, Bonus, ClaimAmount,
        LoanAmount, InterestOnLoanAmount, TotalClaimAmount, NetClaimAmount,
        DeathDate, IntimationDate, TerminationDate, VoucherNo, ClaimId,
        Instalment``.
    """
    fd = parse_iso_date(from_date, "from_date")
    td = parse_iso_date(to_date,   "to_date")
    if fd > td:
        raise ReportError("from_date cannot be after to_date", status=400)

    # Parameter order matches SQL placeholders:
    #   1. group_id  (ge subquery WHERE)
    #   2. group_id  (ged subquery WHERE)
    #   3. from_date (outer WHERE BETWEEN lower bound)
    #   4. to_date   (outer WHERE BETWEEN upper bound)
    with readonly_cursor() as cur:
        cur.execute(SQL, [group_id, group_id, fd, td])
        rows = dictfetchall(cur)

    return [sanitize_row(r) for r in rows]