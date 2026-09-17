"""Group Business Detail Report (New Business / Renewal Business).

Python equivalent of ``proc_copo_BusinessDetail``, querying base tables
directly. The ``vwAccountPostingV2`` view is still available in the live DB
and is referenced directly (it's a system-maintained UNION ALL of
tblCurrentDayPosting + tblPreviousDayPosting + tblPreviousYearsPosting).

Two branches produce a UNIFIED output shape so the frontend can treat them
identically. NB leaves ``Status``, ``Instalment``, ``RiderSA_Renewal`` and
``Paid Date`` as NULL; RB populates them.

Notes
-----
- ``WITH (NOLOCK)`` preserved on all table references, matching the SP.
- ``pd.InstalmenType`` column name has a typo (single 'l') — preserved.
- ``@FilterBy`` chooses which date column to filter on; the date column
  is interpolated in Python from the validated ``filter_by`` input.
- ``vwAccountPostingV2`` is queried directly — view still available.
- Response is a BARE ARRAY (no envelope), preserved from existing view.
- Dates as ISO ``YYYY-MM-DD``; money as ``Decimal`` (DRF serializes as string).
"""
from typing import Any, Dict, List

from .base import (
    ReportError,
    dictfetchall,
    parse_iso_date,
    readonly_cursor,
    sanitize_row,
)


SQL_NB = """
SELECT
    TB2.BranchName,
    tge.Name,
    B.RegisterNo,
    B.PolicyNo,
    B.GroupId,
    CAST(B.SumAssured AS INT)               AS SA,
    CAST(B.Premium AS MONEY)                AS Premium,
    B.Term,
    CAST(B.DOC AS date)                     AS DOC,
    CAST(B.FUP AS date)                     AS NextDueDate,
    CAST(tge.DOB AS date)                   AS DOB,
    CASE
        WHEN tge.Gender = '9'   THEN 'Male'
        WHEN tge.Gender = '10'  THEN 'Female'
        WHEN tge.Gender = '126' THEN 'Others'
        ELSE tge.Gender
    END                                     AS Gender,
    CAST(vapv.ValueDate AS date)            AS ValueDate,
    CAST(vapv.ValueDate AS date)            AS ValueDate_Formatted,
    CAST(B.MaturityDate AS date)            AS MaturityDate,
    CAST(vapv.PaidDate AS date)             AS PaidDate,
    CAST(vapv.PaidDate AS date)             AS PaidDate_Formatted,
    pd.VoucherNo,
    CASE WHEN tge.IsADB = 'Y' THEN 'ADB' ELSE NULL END AS RiderID,
    CAST(B.SumAssured AS INT)               AS RiderSA,
    tge.ExtraPremium                        AS RiderPremium,
    NULL                                    AS [Status],
    NULL                                    AS Instalment,
    NULL                                    AS RiderSA_Renewal,
    NULL                                    AS [Paid Date]
FROM    dbo.vwAccountPostingV2          AS vapv WITH (NOLOCK)
        INNER JOIN tblAccount                    AS E   WITH (NOLOCK) ON E.AccountNo   = vapv.AccountNo
        INNER JOIN dbo.tblGroupEndowmentTermPaid AS pd  WITH (NOLOCK) ON pd.VoucherNo  = vapv.VoucherNo
        INNER JOIN dbo.tblGroupEndowmentDetails  AS B   WITH (NOLOCK) ON pd.PolicyNo   = B.PolicyNo
                                                                          AND pd.RegisterNo = B.RegisterNo
        INNER JOIN dbo.tblGroupEndowment         AS tge WITH (NOLOCK) ON pd.RegisterNo = tge.RegisterNo
        INNER JOIN dbo.tblBranch                 AS TB2 WITH (NOLOCK) ON TB2.Branch    = pd.Branch
WHERE   vapv.GLCode      = '196'
  AND   pd.InstalmenType = 'F'
  AND   vapv.Amount      < 0
  AND   B.GroupId        = %s
  AND   CAST({date_filter_col} AS date) BETWEEN %s AND %s;
"""


SQL_RB = """
SELECT
    TB2.BranchName,
    id.Name,
    pd.RegisterNo,
    pd.PolicyNo,
    pd.GroupId,
    CAST(pd.SumAssured AS INT)              AS SA,
    CAST(tpp.Premium AS MONEY)              AS Premium,
    pd.Term,
    CAST(pd.DOC AS date)                    AS DOC,
    CAST(pd.FUP AS date)                    AS NextDueDate,
    CAST(id.DOB AS date)                    AS DOB,
    CASE
        WHEN id.Gender = '9'   THEN 'Male'
        WHEN id.Gender = '10'  THEN 'Female'
        WHEN id.Gender = '126' THEN 'Others'
        ELSE id.Gender
    END                                     AS Gender,
    CAST(c.ValueDate AS date)              AS ValueDate,
    CAST(c.ValueDate AS date)              AS ValueDate_Formatted,
    CAST(pd.MaturityDate AS date)          AS MaturityDate,
    CAST(c.PaidDate AS date)               AS PaidDate,
    CAST(c.PaidDate AS date)               AS PaidDate_Formatted,
    tpp.VoucherNo,
    CASE WHEN id.IsADB = 'Y' THEN 'ADB' ELSE NULL END AS RiderID,
    CAST(pd.SumAssured AS INT)             AS RiderSA,
    id.ExtraPremium                        AS RiderPremium,
    pd.PolicyStatus                        AS [Status],
    pd.Instalment,
    NULL                                   AS RiderSA_Renewal,
    CAST(c.PaidDate AS date)               AS [Paid Date]
FROM    dbo.vwAccountPostingV2          AS c   WITH (NOLOCK)
        INNER JOIN tblAccount                    AS a   WITH (NOLOCK) ON a.AccountNo   = c.AccountNo
        INNER JOIN dbo.tblGroupEndowmentTermPaid AS tpp WITH (NOLOCK) ON tpp.VoucherNo = c.VoucherNo
        INNER JOIN dbo.tblGroupEndowmentDetails  AS pd  WITH (NOLOCK) ON pd.PolicyNo   = tpp.PolicyNo
                                                                          AND pd.RegisterNo = tpp.RegisterNo
        INNER JOIN dbo.tblGroupEndowment         AS id  WITH (NOLOCK) ON id.RegisterNo = pd.RegisterNo
        INNER JOIN dbo.tblBranch                 AS TB2 WITH (NOLOCK) ON TB2.Branch    = pd.Branch
WHERE   c.VoucherCode     = 'RP'
  AND   c.IsReverse       IS NULL
  AND   pd.Instalment    <> '1'
  AND   c.Amount          < 0
  AND   c.Narration       LIKE 'Renewal Group Endowment Income on%'
  AND   pd.GroupId        = %s
  AND   CAST({date_filter_col} AS date) BETWEEN %s AND %s;
"""


def fetch(group_id: str,
          from_date: str,
          to_date: str,
          filter_by: str,
          flag: str) -> List[Dict[str, Any]]:
    """Return the group business detail report rows.

    Args:
        group_id:  e.g. 'GE1001'
        from_date: ISO date string 'YYYY-MM-DD'
        to_date:   ISO date string 'YYYY-MM-DD'
        filter_by: 'ValueDate' or 'PaidDate' (validated by the view)
        flag:      'NB' for New Business, 'RB' for Renewal Business
                   (validated by the view)

    Returns:
        List of dicts with unified-shape keys: BranchName, Name, RegisterNo,
        PolicyNo, GroupId, SA, Premium, Term, DOC, NextDueDate, DOB, Gender,
        ValueDate, ValueDate_Formatted, MaturityDate, PaidDate,
        PaidDate_Formatted, VoucherNo, RiderID, RiderSA, RiderPremium,
        Status, Instalment, RiderSA_Renewal, 'Paid Date'.
    """
    fd = parse_iso_date(from_date, "from_date")
    td = parse_iso_date(to_date,   "to_date")
    if fd > td:
        raise ReportError("from_date cannot be after to_date", status=400)

    # Pick SQL template and the date column to filter on.
    # filter_by is validated by the view to be 'ValueDate' or 'PaidDate',
    # so interpolating it into SQL is safe.
    if flag == 'NB':
        sql_template = SQL_NB
        date_col = 'vapv.ValueDate' if filter_by == 'ValueDate' else 'vapv.PaidDate'
    else:  # 'RB'
        sql_template = SQL_RB
        date_col = 'c.ValueDate' if filter_by == 'ValueDate' else 'c.PaidDate'

    sql = sql_template.format(date_filter_col=date_col)

    with readonly_cursor() as cur:
        cur.execute(sql, [group_id, fd, td])
        rows = dictfetchall(cur)

    return [sanitize_row(r) for r in rows]