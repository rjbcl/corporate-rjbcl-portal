"""Loan Repayment Report.

Python equivalent of ``proc_copo_GroupReport @Flag='rptGroupPolicyLoanRepayment'``,
querying base tables directly.

Join semantics (mirrors the SP)::

    tblGroupPolicyLoanPaid a (NOLOCK)
    INNER JOIN tblGroupPolicyLoanDetail b (NOLOCK)
        ON b.PolicyNo = a.PolicyNo AND b.LoanId = a.LoanId
    INNER JOIN (SELECT DISTINCT Name, PolicyNo FROM tblGroupEndowment) ge (NOLOCK)
        ON ge.PolicyNo = a.PolicyNo

Filter:
    a.PaidDate BETWEEN ? AND ?
    AND a.Remarks NOT IN ('Paid From Maturity Amount',
                          'Paid From Death Amount',
                          'Paid From Surrender Amount')
    AND a.PolicyNo IN (SELECT PolicyNo FROM tblGroupEndowment WHERE GroupId = ?)

Notes
-----
- The ``@policyNo`` SP parameter is dropped (was always NULL from Django;
  ISNULL fallback made it a no-op).
- The ``@Status`` SP parameter is dropped (this branch never used it).
- The two SQL Server scalar functions ``FN_GetGlCode`` and
  ``FN_GetAccountName`` are called inline — both still exist in the live DB.
- ``tblGroupEndowment`` is queried twice (DISTINCT for Name lookup, and
  for the GroupId filter) — mirrors the SP's two CTE references.
- No ORDER BY in the SP — preserved. Add one here if the frontend needs
  deterministic ordering (e.g. ORDER BY a.PaidDate, a.PolicyNo, a.LoanId).
- ``WITH (NOLOCK)`` preserved on all three table references, matching the SP.
- Dates as ISO ``YYYY-MM-DD``; money/decimal as ``Decimal`` (DRF serializes
  as string).
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
SELECT  a.PolicyNo,
        ge.Name                                 AS FullName,
        a.LoanId,
        CAST(b.LoanDate AS date)                AS LoanDate,
        b.LoanAmount,
        a.Instalment,
        a.DuePrincipal,
        a.PaidPrincipal,
        a.RemainingPrincipal,
        a.PaidInterest,
        a.RemainingInterest,
        CASE WHEN TRY_CAST(a.PaymentFrom AS bigint) IS NOT NULL
                  AND dbo.FN_GetGlCode(a.PaymentFrom) = 171
             THEN a.PaidAmount ELSE 0 END       AS Cash,
        CASE WHEN TRY_CAST(a.PaymentFrom AS bigint) IS NOT NULL
                  AND dbo.FN_GetGlCode(a.PaymentFrom) = 172
             THEN a.PaidAmount ELSE 0 END       AS Cheque,
        CASE WHEN TRY_CAST(a.PaymentFrom AS bigint) IS NOT NULL
                  AND dbo.FN_GetGlCode(a.PaymentFrom) IN (179, 177)
             THEN a.PaidAmount ELSE 0 END       AS Bank,
        CASE WHEN TRY_CAST(a.PaymentFrom AS bigint) IS NOT NULL
             THEN dbo.FN_GetAccountName(a.PaymentFrom)
             ELSE a.PaymentFrom END             AS PaymentFrom,
        b.Status,
        CAST(a.PaidDate AS date)                AS PaidDate,
        CAST(a.ChequeDate AS date)              AS [Tran/Cheque Date],
        a.VoucherNo
FROM    tblGroupPolicyLoanPaid a WITH (NOLOCK)
        INNER JOIN tblGroupPolicyLoanDetail b WITH (NOLOCK)
            ON  b.PolicyNo = a.PolicyNo
            AND b.LoanId   = a.LoanId
        INNER JOIN (SELECT DISTINCT Name, PolicyNo
                    FROM tblGroupEndowment WITH (NOLOCK)) ge
            ON  ge.PolicyNo = a.PolicyNo
WHERE   CAST(a.PaidDate AS date) BETWEEN %s AND %s
  AND   a.Remarks NOT IN (
            'Paid From Maturity Amount',
            'Paid From Death Amount',
            'Paid From Surrender Amount'
        )
  AND   a.PolicyNo IN (
            SELECT PolicyNo
            FROM tblGroupEndowment WITH (NOLOCK)
            WHERE GroupId = %s
        );
"""


def fetch(group_id: str, from_date: str, to_date: str) -> List[Dict[str, Any]]:
    """Return the loan repayment report rows for the given group & range.

    Args:
        group_id: e.g. ``'GE1001'``
        from_date: ISO date string ``'YYYY-MM-DD'`` (filter on a.PaidDate)
        to_date:   ISO date string ``'YYYY-MM-DD'``

    Returns:
        List of dicts with keys: ``PolicyNo, FullName, LoanId, LoanDate,
        LoanAmount, Instalment, DuePrincipal, PaidPrincipal,
        RemainingPrincipal, PaidInterest, RemainingInterest, Cash, Cheque,
        Bank, PaymentFrom, Status, PaidDate, Tran/Cheque Date, VoucherNo``.
    """
    fd = parse_iso_date(from_date, "from_date")
    td = parse_iso_date(to_date,   "to_date")
    if fd > td:
        raise ReportError("from_date cannot be after to_date", status=400)

    # Parameter order: from_date, to_date, group_id (matches SQL placeholders)
    with readonly_cursor() as cur:
        cur.execute(SQL, [fd, td, group_id])
        rows = dictfetchall(cur)

    return [sanitize_row(r) for r in rows]