"""
Port of dbo.proc_copo_surrender_calculator (SQL Server) -> Python.

fetch() returns List[Dict] with 0 or 1 elements (see note at bottom of module)
to match the established `fetch(...) -> List[Dict]` convention while preserving
the SP's "always exactly one collapsed output row" behavior.

ASSUMPTIONS ABOUT api_corporate/reports/base.py (adjust imports/signatures to match
the real helpers if they differ):

    readonly_cursor()          -> context manager yielding a cursor bound to the
                                   'company_external' connection.
    dictfetchall(cursor)       -> List[Dict] from the cursor's current result set.
    sanitize_row(row: Dict)    -> Dict, JSON-safe (Decimal/date -> plain types etc).
    parse_iso_date(s: str)     -> date
    ReportError                -> exception the dispatcher turns into an error response.

DB-CALLED DEPENDENCIES (NOT ported to Python, kept as native SQL calls because their
internals depend on other undocumented tables/functions -- tblAccuralDates,
FN_GroupDynamicPolicyLoanInterest -- that weren't part of this port's scope):

    dbo.FN_GroupPolicyLoanInterestCalculation(@PolicyNo, @ClaimDate)  -- TVF

Everything else (FN_AllNextFUPDate, FullMonthsSeparation, all the procedural
loop/temp-table logic) is reimplemented natively in Python below.

PRESERVED QUIRKS (do not "fix" these without checking with the business/DBA first):
  - SurrenderFactor CASE is a no-op both branches (the -5% discount is disabled
    upstream in the original SP; not reinstated here per instruction).
  - AnniversaryDate is built by naive year/month/day construction (byte-for-byte
    parity with the original string-concat-then-CONVERT approach), and the
    "roll back 12 months if in the future" correction ONLY applies when
    ClaimDate <= MaturityDate - 1 year (see _compute_anniversary_date).
  - Multiple #SurrenderCalculation rows (one per RegisterNo) are aggregated
    (SUM) into a single collapsed output row -- this is intentional.
  - TotalBonus / BonusAfterAdjustment are left as None (SQL NULL) for any
    RegisterNo that had zero matching bonus-rate periods, because the original
    UPDATE...INNER JOIN simply skips those rows rather than defaulting to 0.
    They are excluded from the final SUM(), same as SQL's NULL-skipping SUM.
  - The #tmp_Policy_Bonus SN2 walk includes a "phantom" SN2 == 0 iteration
    (no matching SNo=0 row) and tolerates gaps in SNo caused by the
    `DELETE WHERE EndDate > @LastDueDate` step; PaidInstalment still increments
    on those no-op iterations. Reproduced exactly.
  - LastDueDate is taken from the FIRST inserted row (DOC ASC order, i.e. SN=1)
    to mirror `SELECT TOP 1 ... FROM #SurrenderCalculation` with no ORDER BY,
    which in practice returns the first-inserted row under identity/insert order.
  - @ReducedInstalment / @GroupIdList are never supplied by Django, so the
    ReducedInstalment branch (PaidYear/LastDueDate rollback) and the
    multi-group-id path are dropped; only the `SELECT TOP 1 GroupId` fallback
    is implemented.
  - Loan block intentionally uses two DIFFERENT WHERE clauses across the two
    SELECTs against tblGroupPolicyLoanDetail (one requires ApprovedDate IS NOT
    NULL AND Status='ACTIVE' for @LnDate; the other just Status='ACTIVE' for
    everything else). Preserved exactly per instruction, even though it can
    pick inconsistent rows if a policy has multiple loan records.
  - tblGroupExcessLess lookup has no ORDER BY / TOP 1 in the original, so with
    multiple matching rows SQL Server's scalar variable assignment is
    order-dependent/undefined ("last row wins", order unspecified). We fetch
    all matches and take the last one as returned by the DB, which is the
    closest honest analogue -- true nondeterminism can't be reproduced exactly.
  - TblFiscalYear / @TotalDaysFY is fetched in the original SP but never
    actually used in the final output. Dropped entirely as confirmed dead code.
"""

import math
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional

from .base import readonly_cursor, dictfetchall, sanitize_row, parse_iso_date, ReportError

_GROUP_LIST_REMAINING_PERIOD = {
    "GE1001", "GE1002", "GE1003", "GE1004", "GE1005", "GE1022",
}
_DURATION_MONTHS = 12


# ---------------------------------------------------------------------------
# Native ports of the two simple scalar UDFs (pure date math, no DB access)
# ---------------------------------------------------------------------------

def _as_float(value) -> Optional[float]:
    """DB MONEY/DECIMAL columns come back as decimal.Decimal via pyodbc, which
    cannot be mixed with the plain floats used elsewhere in this module
    (Decimal * float raises TypeError). Cast at every DB boundary."""
    if value is None:
        return None
    return float(value)


def _as_date(value) -> Optional[date]:
    """Normalize a value that may come back from pyodbc as datetime.datetime
    (e.g. tblGroupEndowmentDetails.FUP, which is a `datetime` column even
    though the temp table declared it DATE) into a plain date. Comparing a
    bare `date` against a `datetime` raises TypeError in Python, which is not
    an issue in T-SQL, so every date-typed field pulled off the wire gets
    normalized here before any comparison happens."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    return value


def _add_months(d: date, months: int) -> date:
    """Mirrors SQL Server DATEADD(MONTH, n, d) / DATEADD(YEAR, n, d) semantics,
    including end-of-month clamping (e.g. Jan 31 + 1 month -> Feb 28/29)."""
    month_index = d.month - 1 + months
    year = d.year + month_index // 12
    month = month_index % 12 + 1
    # Clamp day to the last valid day of the target month (SQL Server behavior).
    if month == 12:
        next_month_first = date(year + 1, 1, 1)
    else:
        next_month_first = date(year, month + 1, 1)
    last_day_of_month = (next_month_first - timedelta(days=1)).day
    day = min(d.day, last_day_of_month)
    return date(year, month, day)


def _fn_all_next_fup_date(fup: date, mode: str) -> date:
    """Port of dbo.FN_AllNextFUPDate. Mode is always 'Y' in this SP (@PayMode is
    declared once and never reassigned), so this always takes the ELSE branch
    in practice, but all branches are kept for parity."""
    if mode in ("M", "E"):
        return _add_months(fup, 1)
    elif mode == "Q":
        return _add_months(fup, 3)
    elif mode == "H":
        return _add_months(fup, 6)
    else:
        return _add_months(fup, 12)


def _datediff_months(d1: date, d2: date) -> int:
    """Mirrors SQL Server DATEDIFF(MONTH, d1, d2): counts calendar month
    boundaries crossed, ignoring day-of-month entirely."""
    return (d2.year - d1.year) * 12 + (d2.month - d1.month)


def _fn_full_months_separation(date_a: date, date_b: date) -> int:
    """Byte-for-byte port of dbo.FullMonthsSeparation."""
    if date_a < date_b:
        x, y = date_a, date_b
    else:
        x, y = date_b, date_a

    months = _datediff_months(x, y)
    if x.day > y.day:
        return months - 1
    return months


def _sql_round(value, places: int = 0) -> float:
    """Mirrors SQL Server ROUND(x, n): round-half-away-from-zero, unlike
    Python's default round-half-to-even."""
    if value is None:
        return None
    quantum = Decimal(1).scaleb(-places) if places > 0 else Decimal(1)
    return float(Decimal(str(value)).quantize(quantum, rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# Row-level computation mirroring the #SurrenderCalculation UPDATE chain
# ---------------------------------------------------------------------------

def _compute_anniversary_date(claim_date: date, doc: date, maturity_date: date) -> date:
    """Byte-for-byte port of the string-concat AnniversaryDate construction and
    its conditional 12-month rollback. The rollback only applies when
    claim_date <= maturity_date - 1 year; otherwise the naive construction is
    kept as-is even if it lands after claim_date."""
    anniversary = date(claim_date.year, doc.month, doc.day)

    if claim_date <= _add_months(maturity_date, -12):
        if anniversary > claim_date:
            anniversary = _add_months(anniversary, -12)

    return anniversary


def _build_base_rows(cursor, policy_no: str, group_id: str, claim_date: date) -> List[Dict]:
    cursor.execute(
        """
        SELECT
            ge.PolicyNo   AS PolicyNo,
            ge.RegisterNo AS RegisterNo,
            ge.SumAssured AS SA,
            ge.DOC        AS DOC,
            ge.MaturityDate AS MaturityDate,
            g.Term        AS Term,
            ge.FUP        AS FUP
        FROM tblGroupEndowmentDetails ge
        INNER JOIN tblGroupEndowment g
            ON ge.PolicyNo = g.PolicyNo AND ge.RegisterNo = g.RegisterNo
        WHERE ge.PolicyNo = %s
          AND ge.GroupId = %s
        ORDER BY ge.DOC ASC
        """,
        [policy_no, group_id],
    )
    rows = dictfetchall(cursor)
    for r in rows:
        # Normalize -- FUP/DOC/MaturityDate may come back as datetime;
        # SA is MONEY -> Decimal, cast to float so it can mix with the
        # plain-float math done elsewhere (PaidYear, MAF, etc.)
        r["DOC"] = _as_date(r["DOC"])
        r["FUP"] = _as_date(r["FUP"])
        r["MaturityDate"] = _as_date(r["MaturityDate"])
        r["SA"] = _as_float(r["SA"])
        r["ClaimDate"] = claim_date
        r["PaidYear"] = None
        r["PaidupValue"] = None
        r["RemainingPeriod"] = None
        r["SurrenderFactor"] = None
        r["AnniversaryDate"] = None
        r["RemainingMonth"] = None
        r["MAF"] = None
        r["PaidupValueWithFactor"] = None
        r["TotalBonus"] = None
        r["BonusAfterAdjustment"] = None
    return rows


def _apply_surrender_calculations(
    cursor, rows: List[Dict], claim_date: date, use_term_minus_paidyear: bool
) -> None:
    for r in rows:
        doc, fup, term, sa = r["DOC"], r["FUP"], r["Term"], r["SA"]
        maturity_date = r["MaturityDate"]

        # PaidYear (ReducedInstalment branch dropped -- Django never supplies it)
        r["PaidYear"] = _sql_round(_datediff_months(doc, fup) / 12.0, 0)

        # PaidupValue (NULLIF(Term, 0))
        r["PaidupValue"] = (sa * r["PaidYear"] / term) if term else None

        # RemainingPeriod -- policy-level branch, same decision for every row
        if use_term_minus_paidyear:
            r["RemainingPeriod"] = term - r["PaidYear"]
        else:
            months = _fn_full_months_separation(claim_date, maturity_date)
            r["RemainingPeriod"] = int(months / 12.0)  # truncation, matches CAST(...AS INT)

        # SurrenderFactor lookup (the subsequent CASE adjustment is a no-op; skipped)
        # FLOOR(), not truncation -- matters if RemainingPeriod is ever negative.
        period = math.floor(r["RemainingPeriod"]) if r["RemainingPeriod"] is not None else None
        cursor.execute(
            "SELECT Factor FROM tblSurrenderFactor WITH (NOLOCK) WHERE Period = %s",
            [period],
        )
        factor_row = cursor.fetchone()
        r["SurrenderFactor"] = _as_float(factor_row[0]) if factor_row else None

        # AnniversaryDate + correction
        r["AnniversaryDate"] = _compute_anniversary_date(claim_date, doc, maturity_date)

        # RemainingMonth / MAF / PaidupValueWithFactor
        r["RemainingMonth"] = _fn_full_months_separation(r["AnniversaryDate"], claim_date)
        r["MAF"] = 1 + r["RemainingMonth"] * 0.5 / 100

        if r["PaidupValue"] is not None and r["SurrenderFactor"] is not None:
            r["PaidupValueWithFactor"] = _sql_round(
                r["PaidupValue"] * r["SurrenderFactor"] * r["MAF"] / 1000, 2
            )
        else:
            r["PaidupValueWithFactor"] = None


# ---------------------------------------------------------------------------
# Bonus calculation (#tmp_Policy_Bonus loop)
# ---------------------------------------------------------------------------

def _build_fup_series(doc: date, fup: date, pay_mode: str = "Y", max_iterations: int = 1000) -> List[date]:
    """Mirrors cte_FupSeries: DOC, then successive FN_AllNextFUPDate steps
    while the newly generated date is strictly less than FUP. Capped like the
    original's OPTION (MAXRECURSION 1000)."""
    series = [doc]
    current = doc
    for _ in range(max_iterations):
        nxt = _fn_all_next_fup_date(current, pay_mode)
        if nxt < fup:
            series.append(nxt)
            current = nxt
        else:
            break
    return series


def _fetch_bonus_rate_periods(cursor, doc: date, last_due_date: date) -> List[Dict]:
    cursor.execute(
        """
        SELECT StartDate, EndDate, [Percent]
        FROM tblBonusRate WITH (NOLOCK)
        WHERE PlanID = 1
          AND %s <= EndDate
          AND StartDate <= %s
        ORDER BY StartDate
        """,
        [doc, last_due_date],
    )
    periods = dictfetchall(cursor)
    for p in periods:
        p["StartDate"] = _as_date(p["StartDate"])
        p["EndDate"] = _as_date(p["EndDate"])
        p["Percent"] = _as_float(p["Percent"])
    return periods


def _build_tmp_policy_bonus_for_registration(
    cursor, register_no: str, sa, doc: date, fup: date, last_due_date: date
) -> List[Dict]:
    fup_series = _build_fup_series(doc, fup)
    candidate_periods = _fetch_bonus_rate_periods(cursor, doc, last_due_date)

    matched = []
    for br in candidate_periods:
        b_start, b_end = br["StartDate"], br["EndDate"]
        if any(b_start <= f <= b_end for f in fup_series):
            start_date = doc if b_start <= doc <= b_end else b_start
            end_date = last_due_date if b_start <= last_due_date <= b_end else b_end
            matched.append(
                {
                    "RegisterNo": register_no,
                    "StartDate": start_date,
                    "EndDate": end_date,
                    "BonusRate": br["Percent"],
                    "SA": sa,
                    "NoOfInstallment": None,
                    "BonusYear": None,
                    "TotalBonus": None,
                }
            )

    # SNo = ROW_NUMBER() OVER (ORDER BY br.StartDate) -- assigned BEFORE the delete
    matched.sort(key=lambda x: x["StartDate"])
    for i, row in enumerate(matched, start=1):
        row["SNo"] = i

    # DELETE FROM #tmp_Policy_Bonus WHERE EndDate > @LastDueDate
    matched = [row for row in matched if not (row["EndDate"] > last_due_date)]

    # ComingDueDate walk -- preserves SNo gaps and the phantom SN2==0 iteration
    by_sno = {row["SNo"]: row for row in matched}
    max_sno = max((row["SNo"] for row in matched), default=0)

    coming_due_date = doc
    paid_instalment = 0
    sn2 = 0
    while sn2 <= max_sno:
        row = by_sno.get(sn2)
        if row is not None:
            b_start, b_end = row["StartDate"], row["EndDate"]
            while b_start <= coming_due_date <= b_end:
                coming_due_date = _add_months(coming_due_date, _DURATION_MONTHS)
                if not (b_start <= coming_due_date <= b_end):
                    break
            row["NoOfInstallment"] = paid_instalment
            row["BonusYear"] = paid_instalment * _DURATION_MONTHS / 12.0
        paid_instalment += 1
        sn2 += 1

    return matched


def _compute_bonus_totals(cursor, rows: List[Dict], last_due_date: date) -> None:
    all_bonus_rows: List[Dict] = []
    for r in rows:
        all_bonus_rows.extend(
            _build_tmp_policy_bonus_for_registration(
                cursor, r["RegisterNo"], r["SA"], r["DOC"], r["FUP"], last_due_date
            )
        )

    for row in all_bonus_rows:
        row["TotalBonus"] = (row["SA"] * row["BonusRate"] / 1000) if row["BonusRate"] is not None else 0

    grouped: Dict[str, float] = {}
    for row in all_bonus_rows:
        grouped[row["RegisterNo"]] = grouped.get(row["RegisterNo"], 0) + (row["TotalBonus"] or 0)

    # INNER JOIN semantics: only RegisterNos present in `grouped` get updated;
    # everything else keeps TotalBonus/BonusAfterAdjustment = None (SQL NULL).
    for r in rows:
        if r["RegisterNo"] in grouped:
            total_bonus = grouped[r["RegisterNo"]]
            r["TotalBonus"] = total_bonus
            if r["SurrenderFactor"] is not None:
                r["BonusAfterAdjustment"] = _sql_round(
                    total_bonus * r["SurrenderFactor"] * r["MAF"] / 1000, 2
                )
            else:
                r["BonusAfterAdjustment"] = 0


# ---------------------------------------------------------------------------
# Loan block (preserves the two mismatched WHERE clauses exactly)
# ---------------------------------------------------------------------------

def _compute_loan(cursor, policy_no: str, claim_date: date):
    cursor.execute(
        """
        SELECT ISNULL(LastPaidDate, LoanDate) AS LnDate
        FROM dbo.tblGroupPolicyLoanDetail WITH (NOLOCK)
        WHERE PolicyNo = %s AND ApprovedDate IS NOT NULL AND Status = 'ACTIVE'
        """,
        [policy_no],
    )
    ln_date_row = cursor.fetchone()
    ln_date = _as_date(ln_date_row[0]) if ln_date_row else None

    cursor.execute(
        """
        SELECT
            PrincipalAmount + ISNULL(AccrualAmount, 0) AS LoanAmount,
            RemainingInterest AS RemainingInterest,
            ISNULL(AccrualAmount, 0) AS AccrualInterest1
        FROM dbo.tblGroupPolicyLoanDetail WITH (NOLOCK)
        WHERE PolicyNo = %s AND Status = 'ACTIVE'
        """,
        [policy_no],
    )
    loan_row = cursor.fetchone()
    if loan_row:
        loan_amount, remaining_interest, accrual_interest1 = (
            _as_float(loan_row[0]), _as_float(loan_row[1]), _as_float(loan_row[2])
        )
    else:
        loan_amount, remaining_interest, accrual_interest1 = None, None, None

    cursor.execute(
        "SELECT TotalInterest FROM dbo.FN_GroupPolicyLoanInterestCalculation(%s, %s)",
        [policy_no, claim_date],
    )
    interest_row = cursor.fetchone()
    interest_on_loan = _as_float(interest_row[0]) if interest_row else None

    interest_on_loan = _sql_round(max(interest_on_loan or 0, 0), 0)
    loan_amount = _sql_round(max(loan_amount or 0, 0), 0)

    loan_amount = (loan_amount or 0) - (accrual_interest1 or 0)
    interest_on_loan = (interest_on_loan or 0) + (remaining_interest or 0)

    return loan_amount, interest_on_loan


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def fetch(policy_no: str, claim_date: Optional[str] = None) -> List[Dict]:
    """Port of proc_copo_surrender_calculator.

    Returns a List[Dict] with 0 or 1 elements: empty if the policy/group
    couldn't be resolved (mirrors the original's "no row -> 404" behavior),
    otherwise a single collapsed row with:
    GrossSurrenderValue, Tax, NetSurrenderValue, LoanDeducted, LoanInterest,
    ExcessLess, ClaimDate.
    """
    resolved_claim_date = parse_iso_date(claim_date) if claim_date else date.today()
    print(f"[surrender_calculator] START policy_no={policy_no!r} claim_date={resolved_claim_date!r}")

    with readonly_cursor() as cursor:
        # 1. Resolve GroupId (Django never supplies GroupIdList -> TOP 1 fallback)
        cursor.execute(
            "SELECT TOP 1 GroupId FROM tblGroupEndowment WITH (NOLOCK) WHERE PolicyNo = %s",
            [policy_no],
        )
        group_row = cursor.fetchone()
        print(f"[surrender_calculator] step1 group_row={group_row!r}")
        if not group_row:
            return []
        group_id = group_row[0]

        # 2. Base rows
        rows = _build_base_rows(cursor, policy_no, group_id, resolved_claim_date)
        print(f"[surrender_calculator] step2 base_rows count={len(rows)}")
        for r in rows:
            print(f"[surrender_calculator]   base row: RegisterNo={r['RegisterNo']} "
                  f"SA={r['SA']!r} DOC={r['DOC']!r} FUP={r['FUP']!r} "
                  f"MaturityDate={r['MaturityDate']!r} Term={r['Term']!r}")
        if not rows:
            return []

        use_term_minus_paidyear = group_id in _GROUP_LIST_REMAINING_PERIOD
        print(f"[surrender_calculator] step2b group_id={group_id!r} "
              f"use_term_minus_paidyear={use_term_minus_paidyear}")

        _apply_surrender_calculations(cursor, rows, resolved_claim_date, use_term_minus_paidyear)
        for r in rows:
            print(f"[surrender_calculator]   calc row: RegisterNo={r['RegisterNo']} "
                  f"PaidYear={r['PaidYear']!r} PaidupValue={r['PaidupValue']!r} "
                  f"RemainingPeriod={r['RemainingPeriod']!r} SurrenderFactor={r['SurrenderFactor']!r} "
                  f"AnniversaryDate={r['AnniversaryDate']!r} RemainingMonth={r['RemainingMonth']!r} "
                  f"MAF={r['MAF']!r} PaidupValueWithFactor={r['PaidupValueWithFactor']!r}")

        # 3. LastDueDate: TOP 1 FROM #SurrenderCalculation w/ no ORDER BY
        #    -> mirrors first-inserted row (DOC ASC insert order, i.e. rows[0]).
        #    @ReducedInstalment branch dropped (always NULL from Django).
        last_due_date = _add_months(rows[0]["FUP"], -12)
        print(f"[surrender_calculator] step3 last_due_date={last_due_date!r}")

        # 4. Bonus totals
        _compute_bonus_totals(cursor, rows, last_due_date)
        for r in rows:
            print(f"[surrender_calculator]   bonus row: RegisterNo={r['RegisterNo']} "
                  f"TotalBonus={r['TotalBonus']!r} BonusAfterAdjustment={r['BonusAfterAdjustment']!r}")

        # 5. Loan
        loan_amount, interest_on_loan = _compute_loan(cursor, policy_no, resolved_claim_date)
        print(f"[surrender_calculator] step5 loan_amount={loan_amount!r} interest_on_loan={interest_on_loan!r}")

        # 6. Tax
        cursor.execute(
            """
            SELECT SUM(PaidAmount)
            FROM tblGroupEndowmentDetails WITH (NOLOCK)
            WHERE PolicyNo = %s AND GroupId = %s
            """,
            [policy_no, group_id],
        )
        total_premium_paid = _as_float((cursor.fetchone() or [0])[0]) or 0
        print(f"[surrender_calculator] step6 total_premium_paid={total_premium_paid!r}")

        total_paidup_value_with_factor = sum(
            r["PaidupValueWithFactor"] for r in rows if r["PaidupValueWithFactor"] is not None
        )
        total_bonus_after_adjustment = sum(
            r["BonusAfterAdjustment"] for r in rows if r["BonusAfterAdjustment"] is not None
        )
        print(f"[surrender_calculator] step6b total_paidup_value_with_factor={total_paidup_value_with_factor!r} "
              f"total_bonus_after_adjustment={total_bonus_after_adjustment!r}")

        # ExcessLess: no ORDER BY / TOP 1 in the original -> "last row wins"
        # under SQL Server's undefined scalar-assignment order. Best-effort
        # analogue: take the last row as returned by the DB.
        cursor.execute(
            "SELECT Amount FROM dbo.tblGroupExcessLess WITH (NOLOCK) WHERE PolicyNo = %s",
            [policy_no],
        )
        excess_less_rows = cursor.fetchall()
        excess_less = _as_float(excess_less_rows[-1][0]) if excess_less_rows else None
        print(f"[surrender_calculator] step6c excess_less={excess_less!r} (from {len(excess_less_rows)} rows)")

        tax_amount = _sql_round(
            (total_paidup_value_with_factor + total_bonus_after_adjustment) - total_premium_paid, 0
        )
        if tax_amount < 0:
            tax_amount = 0
        tax = _sql_round(tax_amount * 0.05, 0) if tax_amount > 0 else 0
        print(f"[surrender_calculator] step6d tax_amount={tax_amount!r} tax={tax!r}")

        gross_surrender_value = _sql_round(
            total_paidup_value_with_factor + total_bonus_after_adjustment, 0
        )
        net_surrender_value = _sql_round(
            total_paidup_value_with_factor
            + total_bonus_after_adjustment
            - (loan_amount or 0)
            - (interest_on_loan or 0)
            + (excess_less or 0)
            - (tax or 0),
            0,
        )

        result = {
            "GrossSurrenderValue": gross_surrender_value,
            "Tax": tax or 0,
            "NetSurrenderValue": net_surrender_value,
            "LoanDeducted": loan_amount or 0,
            "LoanInterest": interest_on_loan or 0,
            "ExcessLess": excess_less or 0,
            "ClaimDate": resolved_claim_date,
        }
        print(f"[surrender_calculator] DONE result={result!r}")

        return [sanitize_row(result)]