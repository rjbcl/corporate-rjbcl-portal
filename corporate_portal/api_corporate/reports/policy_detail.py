"""Policy Detail Report.

Returns policy summary (inlined from view_copo_policySummary) plus loan
details for a single policy. Three queries: access check, summary, loans.

Returns a dict (not a list) with keys: summary (List[Dict]), loans (List[Dict]).
The view wraps with success/policy_no metadata.

Notes
-----
- Access check: COUNT(1) in tblGroupEndowment by policy_no + group_ids.
  Raises ReportError(403) if policy not found in user's groups.
- Summary SQL inlines view_copo_policySummary (same as policy_summary.py).
- Loan query has no group filter (access already verified).
- Column case preserved: ``loanID`` (lowercase l), ``Sumassured``,
  ``maturitydate`` (all lowercase).
- No NOLOCK (existing view didn't use it).
- Dates as ISO ``YYYY-MM-DD``; money/decimal as ``Decimal``.
"""
from typing import Any, Dict, List

from .base import (
    ReportError,
    dictfetchall,
    readonly_cursor,
    sanitize_row,
)


SQL_ACCESS_CHECK = """
SELECT COUNT(1)
FROM   tblGroupEndowment
WHERE  PolicyNo = %s
  AND  GroupId IN ({placeholders});
"""


SQL_SUMMARY = """
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
        CAST(a.ClaimDate AS date)      AS ClaimDate,
        a.DistrictID,
        a.WardNo,
        a.NomineePhone,
        a.NomineeAddress,
        COALESCE(s.Value, a.Occupation) AS Occupation,
        b.SumAssured                   AS Sumassured,
        CAST(b.DOC AS date)            AS DOC,
        CAST(b.PaidDate AS date)       AS PaidDate,
        CAST(b.FUP AS date)            AS FUP,
        b.Term,
        b.Premium,
        b.Instalment,
        b.PaidAmount,
        CAST(b.MaturityDate AS date)   AS maturitydate,
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


SQL_LOANS = """
SELECT  PolicyNo,
        LoanId                                AS loanID,
        CAST(LoanDate AS date)                AS LoanDate,
        LoanAmount,
        InterestRate,
        Instalment,
        Status,
        CAST(LastPaidDate AS date)            AS LastPaidDate,
        VoucherNo
FROM    tblGroupPolicyLoanDetail
WHERE   PolicyNo = %s;
"""


def fetch(policy_no: str, group_ids: List[str]) -> Dict[str, Any]:
    """Return policy summary + loan details for a single policy.

    Args:
        policy_no: e.g. 'GE1001-001'
        group_ids: list of GroupId strings the user is authorized to see.

    Returns:
        Dict with keys:
        - ``summary``: List[Dict] — one row per RegisterNo (may be empty).
        - ``loans``: List[Dict] — loan records for this policy (may be empty).

    Raises:
        ReportError(403): if the policy doesn't exist in any of the
            user's groups.
    """
    if not policy_no:
        raise ReportError("policy_no is required", status=400)
    if not group_ids:
        raise ReportError("No groups found for your company", status=403)

    placeholders = ",".join(["%s"] * len(group_ids))

    with readonly_cursor() as cur:
        # 1. Access check
        cur.execute(
            SQL_ACCESS_CHECK.format(placeholders=placeholders),
            [policy_no, *group_ids],
        )
        if cur.fetchone()[0] == 0:
            raise ReportError("Policy not found or access denied", status=403)

        # 2. Summary (inlined view_copo_policySummary)
        cur.execute(
            SQL_SUMMARY.format(placeholders=placeholders),
            [policy_no, *group_ids],
        )
        summary = [sanitize_row(r) for r in dictfetchall(cur)]

        # 3. Loans (no group filter — access already verified)
        cur.execute(SQL_LOANS, [policy_no])
        loans = [sanitize_row(r) for r in dictfetchall(cur)]

    return {'summary': summary, 'loans': loans}