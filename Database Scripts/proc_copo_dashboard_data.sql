CREATE OR ALTER PROCEDURE proc_copo_dashboard_data
    @groupids NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;

    CREATE TABLE #GroupTable (groupid VARCHAR(10) PRIMARY KEY CLUSTERED);

    INSERT INTO #GroupTable (groupid)
    SELECT DISTINCT TRIM(value)
    FROM STRING_SPLIT(@groupids, ',')
    WHERE TRIM(value) <> '';

    --------------------------------------------------
    -- 1. Top 10 latest policies (by DOC)
    --------------------------------------------------
    SELECT TOP 10
        ed.policyNo,
        COALESCE(ge.name, ge.nepname)   AS Name,
        ed.sumassured,
        ed.premium,
        ed.DOC,
        ed.maturitydate
    FROM tblgroupendowmentdetails ed  WITH (NOLOCK)
    INNER JOIN #GroupTable g
        ON ed.groupid = g.groupid
    LEFT JOIN tblgroupendowment ge    WITH (NOLOCK)
        ON ed.policyNo    = ge.policyNo
        AND ed.registerNO = ge.registerNO
    ORDER BY ed.DOC DESC;

    --------------------------------------------------
    -- 2. Summary
    --------------------------------------------------
    SELECT
        COUNT(*)                                                        AS totalPolicies,
        SUM(CASE WHEN ed.policystatus = 'A' THEN 1 ELSE 0 END)           AS activePolicies,
        SUM(CASE WHEN ed.policystatus = 'A' THEN ed.premium ELSE 0 END) AS totalPremium
    FROM tblgroupendowmentdetails ed WITH (NOLOCK)
    INNER JOIN #GroupTable g
        ON ed.groupid = g.groupid;

    --------------------------------------------------
    -- 3. Top 10 FUP data
    --------------------------------------------------
    SELECT TOP 10
        ed.policyNo,
        COALESCE(ge.name, ge.nepname)   AS Name,
        ed.fup,
        DATEDIFF(DAY, GETDATE(), ed.fup) AS DaysUntilFUP
    FROM tblgroupendowmentdetails ed  WITH (NOLOCK)
    INNER JOIN #GroupTable g
        ON ed.groupid = g.groupid
    LEFT JOIN tblgroupendowment ge    WITH (NOLOCK)
        ON ed.policyNo    = ge.policyNo
        AND ed.registerNO = ge.registerNO
    ORDER BY ed.fup DESC;

    DROP TABLE #GroupTable;
END;


-- EXEC proc_copo_dashboard_data 
--     @groupids = '051,057';