"""Group Information — inlined view_copo_groupInformation against base tables."""
from typing import Any, Dict, List

from .base import dictfetchall, readonly_cursor, sanitize_row


SQL = """
;WITH DeduplicatedPolicies AS (
    SELECT  GroupId, PolicyNo, PolicyStatus, Premium, SumAssured,
            ROW_NUMBER() OVER (PARTITION BY PolicyNo ORDER BY PolicyNo) AS rn
    FROM    tblGroupEndowmentDetails
    WHERE   GroupId IN ({placeholders})
),
AggregatedData AS (
    SELECT  GroupId,
            COUNT(DISTINCT PolicyNo)                                              AS total_members_count,
            COUNT(DISTINCT CASE WHEN PolicyStatus = 'A' THEN PolicyNo END)       AS total_active_policies,
            SUM(CASE WHEN rn = 1 THEN Premium    ELSE 0 END)                      AS total_premium,
            SUM(CASE WHEN rn = 1 THEN SumAssured ELSE 0 END)                      AS total_sa,
            COUNT(DISTINCT CASE WHEN PolicyStatus = 'D' THEN PolicyNo END)         AS death_claim,
            COUNT(DISTINCT CASE WHEN PolicyStatus = 'S' THEN PolicyNo END)         AS surrender_claim,
            COUNT(DISTINCT CASE WHEN PolicyStatus = 'M' THEN PolicyNo END)         AS maturity_claim,
            COUNT(DISTINCT CASE WHEN PolicyStatus = 'I' THEN PolicyNo END)         AS transfer_claim,
            COUNT(DISTINCT CASE WHEN PolicyStatus = 'T' THEN PolicyNo END)         AS terminate_claim,
            COUNT(DISTINCT CASE WHEN PolicyStatus IN ('C','cancel')
                                THEN PolicyNo END)                                 AS cancel_claim
    FROM    DeduplicatedPolicies
    GROUP BY GroupId
)
SELECT  gi.GroupId          AS group_id,
        gi.GroupName        AS group_name,
        gi.GroupNameNepali  AS group_name_nepali,
        gi.IsActive         AS is_active,
        ad.total_members_count,
        ad.total_active_policies,
        ad.total_premium,
        ad.total_sa,
        ad.death_claim,
        ad.surrender_claim,
        ad.maturity_claim,
        ad.transfer_claim,
        ad.terminate_claim,
        ad.cancel_claim
FROM    tblGroupInformation gi
        LEFT JOIN AggregatedData ad ON gi.GroupId = ad.GroupId
WHERE   gi.GroupId IN ({placeholders})
ORDER BY gi.GroupId;
"""


def fetch(group_ids: List[str]) -> List[Dict[str, Any]]:
    if not group_ids:
        return []

    placeholders = ",".join(["%s"] * len(group_ids))
    sql = SQL.format(placeholders=placeholders)

    with readonly_cursor() as cur:
        # group_ids passed twice: once for CTE filter, once for final WHERE
        cur.execute(sql, [*group_ids, *group_ids])
        rows = dictfetchall(cur)

    return [sanitize_row(r) for r in rows]