"""Group Transfer Report.

Python equivalent of ``proc_copo_GroupReport @Flag='GroupTransferReport'``,
querying base tables directly.

Join semantics (mirrors the SP)::

    tblGroupEndowment a
    INNER JOIN tblGroupEndowmentDetails c
        ON a.RegisterNo = c.RegisterNo AND a.PolicyNo = c.PolicyNo
    INNER JOIN tblPolicyDetail PD
        ON a.NewRegisterNo = PD.RegisterNo
    LEFT JOIN tblInsuredRiders D
        ON a.NewRegisterNo = D.RegisterNo

Notes
-----
- The ``c`` join is purely a filter (no columns from ``c`` are selected).
  Preserved for parity with the SP.
- ``PD.PolicyNo`` is selected (the *new* policy number after transfer),
  NOT ``a.PolicyNo`` (the pre-transfer policy number). Confirmed intentional.
- LEFT JOIN to ``tblInsuredRiders`` may produce multiple rows per transfer
  when a policy has multiple riders (PK is ``RegisterNo, RiderID``).
  Behavior preserved per business decision.
- The optional ``@Instalment`` SP parameter is dropped — was always NULL
  from the Django layer, so the filter was a no-op.
- ``Term`` is returned as ``smallint`` (number) instead of
  ``CAST(... AS varchar(10))``. Confirmed OK.
- Dates returned as ISO ``YYYY-MM-DD``. Money/Decimal values returned as
  ``Decimal`` (DRF serializes as string).
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
SELECT  a.EmployeeId,
        PD.PolicyNo,
        PD.PreviousPolicy,
        a.GroupId,
        a.Name,
        a.NepName                                AS [Nepali Name],
        CAST(a.DOB AS date)                      AS DOB,
        CAST(a.DOC AS date)                      AS DOC,
        a.SumAssured                             AS SA,
        a.Term                                   AS Term,
        CASE WHEN ISNULL(D.RiderPremium, 0) > 1
             THEN ISNULL(PD.Premium, 0) - ISNULL(D.RiderPremium, 0)
             ELSE a.Premium
        END                                      AS BasicPremium,
        ISNULL(D.RiderPremium, 0)               AS ADB,
        PD.Premium                               AS Premium,
        PD.TotalPremiumPaid                      AS PaidAmount,
        CAST(a.MaturityDate AS date)             AS [Maturity Date],
        PD.Instalment                           AS Instalment,
        CAST(a.TransferDate AS date)             AS TransferDate
FROM    tblGroupEndowment a
        INNER JOIN tblGroupEndowmentDetails c
            ON  a.RegisterNo = c.RegisterNo
            AND a.PolicyNo   = c.PolicyNo
        INNER JOIN tblPolicyDetail PD
            ON  a.NewRegisterNo = PD.RegisterNo
        LEFT JOIN tblInsuredRiders D
            ON  a.NewRegisterNo = D.RegisterNo
WHERE   a.GroupId = %s
  AND   a.TransferDate IS NOT NULL
  AND   CAST(a.TransferDate AS date) BETWEEN %s AND %s
ORDER BY PD.PolicyNo ASC;
"""


def fetch(group_id: str,
          transfer_date_from: str,
          transfer_date_to: str) -> List[Dict[str, Any]]:
    """Return the group transfer report rows for the given group & range.

    Args:
        group_id: e.g. ``'GE1001'``
        transfer_date_from: ISO date string ``'YYYY-MM-DD'``
        transfer_date_to:   ISO date string ``'YYYY-MM-DD'``

    Returns:
        List of dicts with keys: ``EmployeeId, PolicyNo, PreviousPolicy,
        GroupId, Name, Nepali Name, DOB, DOC, SA, Term, BasicPremium, ADB,
        Premium, PaidAmount, Maturity Date, Instalment, TransferDate``.
    """
    fd = parse_iso_date(transfer_date_from, "transfer_date_from")
    td = parse_iso_date(transfer_date_to,   "transfer_date_to")
    if fd > td:
        raise ReportError(
            "transfer_date_from cannot be after transfer_date_to",
            status=400,
        )

    with readonly_cursor() as cur:
        cur.execute(SQL, [group_id, fd, td])
        rows = dictfetchall(cur)

    return [sanitize_row(r) for r in rows]