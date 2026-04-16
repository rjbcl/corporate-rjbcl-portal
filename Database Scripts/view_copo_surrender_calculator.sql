CREATE OR ALTER VIEW view_copo_surrender_calculator AS
SELECT
  e.policyNO,
  e.groupid,
    -- Loan check: stops at first match, never full-scans
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM tblGrouppolicyloandetail l
            WHERE l.policyNO = e.policyNO
              AND l.status IN ('active', 'approved', 'registered')
        )
        THEN 1 ELSE 0
    END AS hasActiveLoan,

    -- Pre-aggregated in the same pass, no correlated subquery
    SUM(e.sumAssured) AS SurrenderAmount

FROM tblgroupendowmentdetails e
GROUP BY e.policyNO , e.groupid;


-- SELECT hasActiveLoan, SurrenderAmount
-- FROM view_copo_surrender_calculator
-- WHERE policyNO = '05209437';

--Allow 
-- 05208669


--Disallow
-- 05209437