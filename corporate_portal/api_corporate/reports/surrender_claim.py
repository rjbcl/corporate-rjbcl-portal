"""Surrender Claim Report.

Python equivalent of ``proc_copo_GroupReport @Flag='GroupSurrenderReport'``.

Notes
-----
- CTE 1 (endowment agg) has NO GroupId filter — only PolicyStatus='S'.
  (Different from death claim, which filtered both.) Preserve.
- CTE 2 (details agg) has GroupId filter but NO PolicyStatus filter.
  (Different from death claim.) Preserve.
- GroupId is filtered in the outer WHERE via ``b.GroupId = %s``.
- ``SNo`` = ROW_NUMBER() OVER (ORDER BY a.CreatedDate DESC). No ORDER BY
  in the final SELECT (preserved from SP).
- ``SurrenderAmount`` ← ``a.SurrenderValue`` (alias).
- ``LoanAmount``     ← ``a.TotalLoanAmount`` (alias).
- ``LoanInterest``    ← ``a.CalculatedInterest`` (alias).
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
SELECT  ROW_NUMBER() OVER (ORDER BY a.CreatedDate DESC) AS SNo,
        a.GroupId,
        b.PolicyNo,
        b.EmployeeId,
        b.Name,
        b.NepName,
        CAST(b.DOB AS date)               AS DOB,
        CAST(b.DOC AS date)               AS DOC,
        b.SA,
        b.Premium,
        b.Term,
        CAST(b.MaturityDate AS date)      AS MaturityDate,
        a.SurrenderValue                   AS SurrenderAmount,
        CAST(a.SurrenderDate AS date)      AS SurrenderDate,
        CAST(a.IntimationDate AS date)     AS IntimationDate,
        a.VoucherNo,
        a.Tax,
        a.TotalLoanAmount                  AS LoanAmount,
        a.CalculatedInterest               AS LoanInterest,
        a.NetPayable,
        a.ClaimId,
        c.Instalment
FROM    tblGroupSurrender a
        INNER JOIN (
            -- CTE 1: tempGroupEndowment — NO GroupId filter (matches SP)
            SELECT  PolicyNo, EmployeeId, GroupId, Name, NepName, DOB,
                    MIN(DOC)        AS DOC,
                    SUM(Premium)    AS Premium,
                    SUM(SumAssured) AS SA,
                    MAX(Term)       AS Term,
                    MaturityDate
            FROM    tblGroupEndowment
            WHERE   PolicyStatus = 'S'
            GROUP BY EmployeeId, PolicyNo, GroupId, Name, NepName, DOB, MaturityDate
        ) b ON a.PolicyNo = b.PolicyNo
        INNER JOIN (
            -- CTE 2: tempGroupEndowmentDetails — GroupId filter, no status filter
            SELECT  PolicyNo, MAX(Instalment) AS Instalment
            FROM    tblGroupEndowmentDetails
            WHERE   GroupId = %s
            GROUP BY PolicyNo
        ) c ON a.PolicyNo = c.PolicyNo
WHERE   b.GroupId = %s
  AND   CAST(a.SurrenderPaidDate AS date) BETWEEN %s AND %s;
"""


def fetch(group_id: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
    """Return the surrender claim report rows for the given group & range.

    Args:
        group_id: e.g. 'GE1001'
        from_date: ISO date string 'YYYY-MM-DD' (filter on a.SurrenderPaidDate)
        to_date:   ISO date string 'YYYY-MM-DD'

    Returns:
        List of dicts with keys: SNo, GroupId, PolicyNo, EmployeeId, Name,
        NepName, DOB, DOC, SA, Premium, Term, MaturityDate, SurrenderAmount,
        SurrenderDate, IntimationDate, VoucherNo, Tax, LoanAmount,
        LoanInterest, NetPayable, ClaimId, Instalment.
    """
    fd = parse_iso_date(from_date, "from_date")
    td = parse_iso_date(to_date,   "to_date")
    if fd > td:
        raise ReportError("from_date cannot be after to_date", status=400)

    # Param order: group_id (c subquery), group_id (outer WHERE b.GroupId),
    # from_date, to_date (BETWEEN bounds)
    with readonly_cursor() as cur:
        cur.execute(SQL, [group_id, group_id, fd, td])
        rows = dictfetchall(cur)

    return [sanitize_row(r) for r in rows]