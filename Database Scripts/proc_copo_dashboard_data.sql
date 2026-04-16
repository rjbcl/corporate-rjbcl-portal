CREATE OR ALTER PROCEDURE proc_copo_dashboard_data
    @groupids NVARCHAR(MAX)
AS
BEGIN
    SET NOCOUNT ON;

    declare @totalPolicys int, @activePolicies int, @totalPremium decimal(18,2);

    CREATE TABLE #GroupTable (groupid VARCHAR(10) PRIMARY KEY );

    INSERT INTO #GroupTable (groupid)
    SELECT DISTINCT TRIM(value)
    FROM STRING_SPLIT(@groupids, ',')
    WHERE TRIM(value) <> '';

 SELECT TOP 10
        ed.policyNo,
        COALESCE(ge.name, ge.nepname)  AS Name,
        SUM(ISNULL(ed.sumassured, 0)) AS sumassured,
        SUM(ISNULL(ed.premium, 0)) AS premium,
        MIN(ed.DOC) AS DOC,
        MAX(ed.maturitydate) AS maturitydate
    FROM tblgroupendowmentdetails ed  WITH (NOLOCK)
    INNER JOIN #GroupTable g ON ed.groupid = g.groupid
    LEFT JOIN tblgroupendowment ge WITH (NOLOCK) ON ed.policyNo = ge.policyNo AND ed.registerNO = ge.registerNO
    WHERE ed.sumassured > 0 AND ed.premium > 0 AND ed.policystatus = 'A'
    GROUP BY ed.policyNo, COALESCE(ge.name, ge.nepname)
    ORDER BY MIN(ed.DOC) DESC;
    --------------------------------------------------
    -- 2. Summary
    --------------------------------------------------

   
    SELECT TOP 1
        @totalPolicys = COUNT(distinct ed.policyNo),
        @activePolicies = COUNT(DISTINCT CASE WHEN ed.policystatus = 'A' THEN ed.policyNo ELSE NULL END),
        @totalPremium = SUM(CASE WHEN ed.policystatus = 'A' THEN ed.premium ELSE 0 END)
    FROM tblgroupendowmentdetails ed WITH (NOLOCK)
    INNER JOIN #GroupTable g
        ON ed.groupid = g.groupid;
    select @totalPolicys as totalPolicies, @activePolicies as activePolicies, @totalPremium as totalPremium;

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