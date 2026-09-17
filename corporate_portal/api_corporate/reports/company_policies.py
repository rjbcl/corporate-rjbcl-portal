"""Company Policies — replaces GroupEndowment model/ViewSet with raw SQL.

Inlines view_copo_groupEndowment (INNER JOIN of tblGroupEndowment +
tblGroupEndowmentDetails) and provides:
- fetch_list(): paginated list with search/filter/ordering
- fetch_statistics(): aggregate counts and sums
- fetch_by_company(): filtered list by company's groups

Column aliases are snake_case to match GroupEndowmentSerializer output.
"""
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from .base import (
    ReportError,
    dictfetchall,
    readonly_cursor,
    sanitize_row,
)


# ---------------------------------------------------------------------------
# Shared column list — maps every model field to its source table + alias.
# ged.* fields come from tblGroupEndowmentDetails (per the view definition).
# ge.*  fields come from tblGroupEndowment.
# ---------------------------------------------------------------------------

COLUMNS = """
    ged.RegisterNo           AS register_no,
    ged.PolicyNo             AS policy_no,
    ged.GroupId              AS group_id,
    CAST(ged.DOC AS date)     AS doc,
    ged.Term                AS term,
    ged.SumAssured           AS sum_assured,
    ged.Premium              AS premium,
    CAST(ged.FUP AS date)     AS fup,
    CAST(ged.MaturityDate AS date) AS maturity_date,
    ged.PolicyStatus         AS policy_status,
    ged.PolicyType           AS policy_type,
    ged.LateFine             AS late_fine,
    CAST(ged.PaidDate AS date) AS paid_date,
    ged.Instalment           AS instalment,
    ged.PaidAmount           AS paid_amount,
    ged.BatchNo              AS batch_no,
    ged.Intrest              AS intrest,
    ged.ClaimStatus          AS claim_status,
    ged.LateFinePercent      AS late_fine_percent,
    ged.ReducedInstalment    AS reduced_instalment,
    ge.Branch               AS branch,
    ge.EmployeeId            AS employee_id,
    ge.Name                 AS name,
    ge.NepName              AS nep_name,
    ge.Gender               AS gender,
    ge.Occupation           AS occupation,
    CAST(ge.DOB AS date)    AS dob,
    ge.ExtraPremium          AS extra_premium,
    ge.TotalPremium          AS total_premium,
    ge.Address               AS address,
    ge.Email                 AS email,
    ge.Mobile                AS mobile,
    ge.ADB                   AS adb,
    ge.OccExtraAmount        AS occ_extra_amount,
    ge.ADBDiscount           AS adb_discount,
    ge.FatherName            AS father_name,
    ge.MotherName            AS mother_name,
    ge.NomineeName           AS nominee_name,
    ge.NomineeAddress        AS nominee_address,
    ge.PhoneNumberResidence  AS phone_number_residence,
    CAST(ge.TransferDate AS date) AS transfer_date,
    CAST(ge.DuplicatePolicyDate AS date) AS duplicate_policy_date,
    CAST(ge.LapseDate AS date) AS lapse_date,
    CAST(ge.LapseActiveDate AS date) AS lapse_active_date,
    CAST(ge.DOE AS date)    AS doe,
    ge.BasicPremium          AS basic_premium,
    ge.IsADB                 AS is_adb,
    ge.AfterDisRebateRate    AS after_dis_rebate_rate,
    ge.FiscalYear            AS fiscal_year,
    ge.NomineeRelationship   AS nominee_relationship,
    CAST(ge.ClaimDate AS date) AS claim_date,
    CAST(ge.TerminationDate AS date) AS termination_date,
    ge.PlanId                AS plan_id,
    ge.IsMultiplePolicyIssued AS is_multiple_policy_issued
"""

FROM_CLAUSE = """
    tblGroupEndowment ge
    INNER JOIN tblGroupEndowmentDetails ged
        ON ge.RegisterNo = ged.RegisterNo
        AND ge.PolicyNo = ged.PolicyNo
"""

# Map of filterset field name -> SQL column reference
FILTER_MAP = {
    'policy_status':     'ged.PolicyStatus',
    'fiscal_year':       'ge.FiscalYear',
    'gender':            'ge.Gender',
    'policy_type':       'ged.PolicyType',
    'is_adb':            'ge.IsADB',
    'employee_id':       'ge.EmployeeId',
    'claim_status':      'ged.ClaimStatus',
    'group_id':          'ged.GroupId',
    'register_no':       'ged.RegisterNo',
}

# Map of search field -> SQL LIKE pattern
SEARCH_MAP = {
    'name':         'ge.Name',
    'nep_name':     'ge.NepName',
    'policy_no':    'ged.PolicyNo',
    'employee_id':  'ge.EmployeeId',
    'mobile':       'ge.Mobile',
    'email':        'ge.Email',
    'register_no':  'ged.RegisterNo',
}

# Map of ordering field -> SQL column
ORDER_MAP = {
    'maturity_date': 'ged.MaturityDate',
    'doc':           'ged.DOC',
    'name':          'ge.Name',
    'premium':       'ged.Premium',
    'sum_assured':   'ged.SumAssured',
    'group_id':      'ged.GroupId',
    'register_no':   'ged.RegisterNo',
    'policy_no':     'ged.PolicyNo',
}


# ---------------------------------------------------------------------------
# fetch_statistics — aggregate counts and sums
# ---------------------------------------------------------------------------

def fetch_statistics(group_ids: List[str]) -> Dict[str, Any]:
    """Return aggregate statistics for the given group IDs."""
    if not group_ids:
        return {
            'total_policies': 0,
            'active_policies': 0,
            'lapsed_policies': 0,
            'inactive_policies': 0,
            'total_sum_assured': 0,
            'total_premium': 0,
        }

    placeholders = ",".join(["%s"] * len(group_ids))

    sql = f"""
    SELECT
        COUNT(DISTINCT ged.PolicyNo)                                          AS total_policies,
        COUNT(DISTINCT CASE WHEN ged.PolicyStatus = 'A' THEN ged.PolicyNo END) AS active_policies,
        COUNT(DISTINCT CASE WHEN ged.PolicyStatus = 'L' THEN ged.PolicyNo END) AS lapsed_policies,
        SUM(CASE WHEN ged.PolicyStatus = 'A' THEN ged.SumAssured ELSE 0 END)   AS total_sum_assured,
        SUM(CASE WHEN ged.PolicyStatus = 'A' THEN ged.Premium    ELSE 0 END)   AS total_premium
    FROM tblGroupEndowmentDetails ged
    WHERE ged.GroupId IN ({placeholders});
    """

    with readonly_cursor() as cur:
        cur.execute(sql, group_ids)
        row = cur.fetchone()

    total = row[0] or 0
    active = row[1] or 0
    lapsed = row[2] or 0
    total_sa = row[3] or 0
    total_prem = row[4] or 0

    return {
        'total_policies': total,
        'active_policies': active,
        'lapsed_policies': lapsed,
        'inactive_policies': total - active - lapsed,
        'total_sum_assured': float(total_sa),
        'total_premium': float(total_prem),
    }


# ---------------------------------------------------------------------------
# fetch_by_company — filtered list (no pagination)
# ---------------------------------------------------------------------------

def fetch_by_company(group_ids: List[str]) -> List[Dict[str, Any]]:
    """Return all endowment rows for the given group IDs (no pagination)."""
    if not group_ids:
        return []

    placeholders = ",".join(["%s"] * len(group_ids))

    sql = f"""
    SELECT {COLUMNS}
    FROM {FROM_CLAUSE}
    WHERE ged.GroupId IN ({placeholders})
    ORDER BY ged.MaturityDate DESC;
    """

    with readonly_cursor() as cur:
        cur.execute(sql, group_ids)
        rows = dictfetchall(cur)

    return [sanitize_row(r) for r in rows]


# ---------------------------------------------------------------------------
# fetch_list — paginated list with search/filter/ordering
# ---------------------------------------------------------------------------

def fetch_list(
    group_ids: List[str],
    page: int = 1,
    page_size: int = 100,
    search: Optional[str] = None,
    filters: Optional[Dict[str, str]] = None,
    ordering: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a paginated list of endowment rows with search/filter/ordering.

    Returns a DRF-style pagination response:
        {count, next, previous, results}
    """
    params: List[Any] = []
    where_clauses: List[str] = []

    if group_ids:
        placeholders = ",".join(["%s"] * len(group_ids))
        where_clauses.append(f"ged.GroupId IN ({placeholders})")
        params.extend(group_ids)
    search_clauses: List[str] = []

    # ── Filters (exact match) ──
    if filters:
        for field, value in filters.items():
            col = FILTER_MAP.get(field)
            if col and value:
                where_clauses.append(f"{col} = %s")
                params.append(value)

    # ── Search (LIKE on multiple fields) ──
    if search:
        for field, col in SEARCH_MAP.items():
            search_clauses.append(f"{col} LIKE %s")
            params.append(f"%{search}%")
        if search_clauses:
            where_clauses.append(f"({' OR '.join(search_clauses)})")

    where_sql = " AND ".join(where_clauses)

    # ── Ordering ──
    order_sql = "ged.MaturityDate DESC"  # default
    if ordering:
        direction = "DESC" if ordering.startswith("-") else "ASC"
        field = ordering.lstrip("-")
        col = ORDER_MAP.get(field)
        if col:
            order_sql = f"{col} {direction}"

    offset = (page - 1) * page_size

    # ── Count query ──
    count_sql = f"SELECT COUNT(*) FROM {FROM_CLAUSE} WHERE {where_sql};"

    # ── Data query ──
    data_sql = f"""
    SELECT {COLUMNS}
    FROM {FROM_CLAUSE}
    WHERE {where_sql}
    ORDER BY {order_sql}
    OFFSET {offset} ROWS FETCH NEXT {page_size} ROWS ONLY;
    """

    with readonly_cursor() as cur:
        cur.execute(count_sql, params)
        total = cur.fetchone()[0]

        cur.execute(data_sql, params)
        rows = [sanitize_row(r) for r in dictfetchall(cur)]

    # Build pagination URLs (relative — frontend adds base URL)
    next_url = f"?page={page + 1}" if (offset + page_size) < total else None
    previous_url = f"?page={page - 1}" if page > 1 else None

    return {
        'count': total,
        'next': next_url,
        'previous': previous_url,
        'results': rows,
    }