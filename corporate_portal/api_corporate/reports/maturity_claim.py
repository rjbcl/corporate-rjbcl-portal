"""Maturity Claim Report.

Python equivalent of ``proc_copo_GroupReport @Flag='GroupMaturityReport'``.

Join semantics (mirrors the SP)::

    tblGroupMaturity A
    LEFT JOIN (
        -- tempGroupEndowmentMaturity: aggregated endowment rows for matured policies
        SELECT PolicyNo, EmployeeId, GroupId, Name, NepName, DOB,
               MIN(DOC) AS DOC, SUM(Premium) AS Premium, SUM(SumAssured) AS SA,
               MaturityDate
        FROM tblGroupEndowment
        WHERE PolicyStatus = 'M' AND GroupId = ?
        GROUP BY EmployeeId, PolicyNo, GroupId, Name, NepName, DOB, MaturityDate
    ) b ON A.PolicyNo = b.PolicyNo

Filter:
    A.GroupId = ?  AND  A.PaidDate BETWEEN ? AND ?

Notes
-----
- LEFT JOIN (not INNER) — a maturity claim with no matching endowment row
  still appears, with NULL for all b.* columns (including b.PolicyNo).
- ``NetClaimAmount`` = ``A.TotalClaimAmount - A.TotalTax - A.LoanAmount
  - A.CalculatedInterest``. NO ISNULL coalescing — NULL propagates.
- ``Term`` dropped from subquery (dead column, CTE 2 never used b.Term).
- No NOLOCK (SP didn't use it here).
- Response is a BARE ARRAY (no envelope).
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
SELECT  A.GroupId,
        b.PolicyNo,
        b.EmployeeId,
        b.Name,
        b.NepName,
        CAST(b.DOB AS date)               AS DOB,
        b.SA,
        b.Premium,
        CAST(b.DOC AS date)               AS DOC,
        CAST(b.MaturityDate AS date)      AS MaturityDate,
        A.TotalBonus                        AS Bonus,
        A.TotalTax,
        A.TotalClaimAmount                  AS ClaimAmount,
        A.LoanAmount,
        A.CalculatedInterest,
        A.TotalClaimAmount - A.TotalTax - A.LoanAmount - A.CalculatedInterest
                                            AS NetClaimAmount,
        CAST(A.ClaimDate AS date)           AS ClaimDate,
        A.VoucherNo,
        A.ClaimId
FROM    tblGroupMaturity A
        LEFT JOIN (
            SELECT  PolicyNo, EmployeeId, GroupId, Name, NepName, DOB,
                    MIN(DOC)        AS DOC,
                    SUM(Premium)    AS Premium,
                    SUM(SumAssured) AS SA,
                    MaturityDate
            FROM    tblGroupEndowment
            WHERE   PolicyStatus = 'M'
              AND   GroupId = %s
            GROUP BY EmployeeId, PolicyNo, GroupId, Name, NepName, DOB, MaturityDate
        ) b ON A.PolicyNo = b.PolicyNo
WHERE   A.GroupId = %s
  AND   CAST(A.PaidDate AS date) BETWEEN %s AND %s;
"""


def fetch(group_id: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
    """Return the maturity claim report rows for the given group & range.

    Args:
        group_id: e.g. 'GE1001'
        from_date: ISO date string 'YYYY-MM-DD' (filter on A.PaidDate)
        to_date:   ISO date string 'YYYY-MM-DD'

    Returns:
        List of dicts with keys: GroupId, PolicyNo, EmployeeId, Name, NepName,
        DOB, SA, Premium, DOC, MaturityDate, Bonus, TotalTax, ClaimAmount,
        LoanAmount, CalculatedInterest, NetClaimAmount, ClaimDate, VoucherNo,
        ClaimId.
    """
    fd = parse_iso_date(from_date, "from_date")
    td = parse_iso_date(to_date,   "to_date")
    if fd > td:
        raise ReportError("from_date cannot be after to_date", status=400)

    # Param order: group_id (subquery), group_id (outer WHERE),
    # from_date, to_date (BETWEEN bounds)
    with readonly_cursor() as cur:
        cur.execute(SQL, [group_id, group_id, fd, td])
        rows = dictfetchall(cur)

    return [sanitize_row(r) for r in rows]