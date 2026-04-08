SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE OR ALTER PROCEDURE [dbo].[proc_copo_surrender_calculator]
(
    @PolicyNo VARCHAR(50)
)
AS
SET NOCOUNT ON
BEGIN

    DECLARE @ClaimDate  DATE = CAST(GETDATE() AS DATE)
    DECLARE @GroupId    VARCHAR(50)
    DECLARE @LastDueDate DATE
    DECLARE @PayMode    CHAR(1)  = 'Y'
    DECLARE @Duration   INT      = 12         -- hardcoded Y mode
    DECLARE @HasActiveLoan BIT

    -- Scalar loop variables (still needed for the per-policy bonus loop)
    DECLARE @SN INT, @SNCounter INT
    DECLARE @SN2 INT, @SNCounter2 INT
    DECLARE @SA MONEY, @DOC DATE, @FUP DATE, @RegisterNo VARCHAR(100)
    DECLARE @Fupforbonuscalculation DATE
    DECLARE @ComingDueDate DATETIME, @PaidInstalment INT
    DECLARE @BonusStartDate DATETIME, @BonusEndDate DATETIME

    -- =========================================================
    -- 1. Resolve GroupId
    -- =========================================================
    SELECT TOP 1 @GroupId = GroupId
    FROM tblGroupEndowment
    WHERE PolicyNo = @PolicyNo

    -- =========================================================
    -- 2. Build #SurrenderCalculation in one pass via CTE
    --    Replaces 9 chained UPDATEs on the same temp table
    -- =========================================================
    CREATE TABLE #SurrenderCalculation
    (
        SN                    INT IDENTITY(1,1),
        PolicyNo              VARCHAR(100) NULL,
        RegisterNo            VARCHAR(100) NULL,
        SA                    MONEY        NULL,
        DOC                   DATE         NULL,
        MaturityDate          DATE         NULL,
        ClaimDate             DATE         NULL,
        Term                  INT          NULL,
        FUP                   DATE         NULL,
        PaidYear              FLOAT        NULL,
        PaidupValue           MONEY        NULL,
        RemainingPeriod       FLOAT        NULL,
        SurrenderFactor       FLOAT        NULL,
        AnniversaryDate       DATE         NULL,
        RemainingMonth        FLOAT        NULL,
        MAF                   FLOAT        NULL,
        PaidupValueWithFactor MONEY        NULL,
        TotalBonus            MONEY        NULL,
        BonusAfterAdjustment  MONEY        NULL
    )

    ;WITH cte_Base AS
    (
        -- Raw join between policy details and group
        SELECT
            ge.PolicyNo,
            ge.RegisterNo,
            ge.SumAssured                                           AS SA,
            ge.DOC,
            ge.MaturityDate,
            @ClaimDate                                              AS ClaimDate,
            g.Term,
            ge.FUP
        FROM tblGroupEndowmentDetails ge
        INNER JOIN tblGroupEndowment g
            ON ge.PolicyNo   = g.PolicyNo
            AND ge.RegisterNo = g.RegisterNo
        WHERE ge.PolicyNo = @PolicyNo
          AND ge.GroupId  = @GroupId
    ),
    cte_PaidYear AS
    (
        -- PaidYear and PaidupValue (ReducedInstalment is always NULL here)
        SELECT *,
            ROUND(DATEDIFF(MM, DOC, FUP) / 12.0, 0)               AS PaidYear
        FROM cte_Base
    ),
    cte_PaidupValue AS
    (
        SELECT *,
            (SA * PaidYear) / NULLIF(Term, 0)                      AS PaidupValue
        FROM cte_PaidYear
    ),
    cte_RemainingPeriod AS
    (
        SELECT *,
            CASE
                WHEN @GroupId IN ('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
                THEN (Term - PaidYear)
                ELSE CAST(CONVERT(INT, dbo.FullMonthsSeparation(ClaimDate, MaturityDate)) / 12.0 AS INT)
            END                                                     AS RemainingPeriod
        FROM cte_PaidupValue
    ),
    cte_SurrenderFactor AS
    (
        SELECT r.*,
            sf.Factor                                               AS SurrenderFactor
        FROM cte_RemainingPeriod r
        LEFT JOIN tblSurrenderFactor sf (NOLOCK)
            ON sf.PERIOD = FLOOR(r.RemainingPeriod)
    ),
    cte_Anniversary AS
    (
        -- Build anniversary date and roll back one year if needed
        SELECT *,
            CASE
                WHEN @ClaimDate <= DATEADD(YEAR, -1, MaturityDate)
                THEN
                    CASE
                        WHEN DATEFROMPARTS(YEAR(ClaimDate), MONTH(DOC), DAY(DOC)) > ClaimDate
                        THEN DATEADD(MM, -12, DATEFROMPARTS(YEAR(ClaimDate), MONTH(DOC), DAY(DOC)))
                        ELSE DATEFROMPARTS(YEAR(ClaimDate), MONTH(DOC), DAY(DOC))
                    END
                ELSE DATEFROMPARTS(YEAR(ClaimDate), MONTH(DOC), DAY(DOC))
            END                                                     AS AnniversaryDate
        FROM cte_SurrenderFactor
    ),
    cte_MAF AS
    (
        SELECT *,
            dbo.FullMonthsSeparation(AnniversaryDate, ClaimDate)   AS RemainingMonth
        FROM cte_Anniversary
    ),
    cte_Final AS
    (
        SELECT *,
            1 + RemainingMonth * 0.5 / 100                         AS MAF
        FROM cte_MAF
    )
    INSERT INTO #SurrenderCalculation
        (PolicyNo, RegisterNo, SA, DOC, MaturityDate, ClaimDate, Term, FUP,
         PaidYear, PaidupValue, RemainingPeriod, SurrenderFactor,
         AnniversaryDate, RemainingMonth, MAF, PaidupValueWithFactor)
    SELECT
        PolicyNo, RegisterNo, SA, DOC, MaturityDate, ClaimDate, Term, FUP,
        PaidYear, PaidupValue, RemainingPeriod, SurrenderFactor,
        AnniversaryDate, RemainingMonth, MAF,
        ROUND((PaidupValue * SurrenderFactor * MAF) / 1000, 2)     AS PaidupValueWithFactor
    FROM cte_Final
    ORDER BY DOC ASC

    -- =========================================================
    -- 3. LastDueDate (PayMode = Y, ReducedInstalment = NULL)
    -- =========================================================
    SELECT TOP 1 @LastDueDate = DATEADD(YEAR, -1, FUP)
    FROM #SurrenderCalculation

    -- =========================================================
    -- 4. Bonus calculation
    --    Inner #tempFup1 loop replaced with a recursive CTE
    --    that generates the full FUP date series set-based
    -- =========================================================
    CREATE TABLE #tmp_Policy_Bonus
    (
        SNo             INT,
        RegisterNo      VARCHAR(100),
        StartDate       DATETIME,
        EndDate         DATETIME,
        BonusRate       INT,
        NoOfInstallment INT,
        BonusYear       MONEY,
        SA              MONEY,
        TotalBonus      MONEY
    )

    SELECT @SNCounter = MAX(SN) FROM #SurrenderCalculation
    SET @SN = 1

    WHILE @SN <= @SNCounter
    BEGIN
        SELECT
            @SA         = SA,
            @DOC        = DOC,
            @FUP        = FUP,
            @RegisterNo = RegisterNo
        FROM #SurrenderCalculation
        WHERE SN = @SN

        -- Recursive CTE replaces the row-by-row #tempFup1 WHILE loop
        ;WITH cte_FupSeries AS
        (
            SELECT CAST(@DOC AS DATE) AS FUP   -- anchor
            UNION ALL
            SELECT CAST(dbo.FN_AllNextFUPDate(FUP, @PayMode) AS DATE)
            FROM cte_FupSeries
            WHERE CAST(dbo.FN_AllNextFUPDate(FUP, @PayMode) AS DATE) < @FUP
        )
        INSERT INTO #tmp_Policy_Bonus (SNo, RegisterNo, StartDate, EndDate, BonusRate, SA)
        SELECT
            ROW_NUMBER() OVER (ORDER BY br.StartDate),
            @RegisterNo,
            CASE WHEN @DOC BETWEEN br.StartDate AND br.EndDate THEN @DOC ELSE br.StartDate END,
            CASE WHEN @LastDueDate BETWEEN br.StartDate AND br.EndDate THEN @LastDueDate ELSE br.EndDate END,
            br.[Percent],
            @SA
        FROM tblBonusRate br (NOLOCK)
        WHERE br.[PlanID] = 1
          AND @DOC       <= br.EndDate
          AND br.StartDate <= @LastDueDate
          AND EXISTS (
                SELECT 1 FROM cte_FupSeries f
                WHERE f.FUP BETWEEN br.StartDate AND br.EndDate
              )
        OPTION (MAXRECURSION 1000)

        -- Remove any rows that leaked past LastDueDate after the date clamp above
        DELETE FROM #tmp_Policy_Bonus WHERE EndDate > @LastDueDate

        -- Count instalments per bonus band
        SET @SN2 = 0
        SELECT @SNCounter2   = MAX(SNo)  FROM #tmp_Policy_Bonus
        SET @ComingDueDate   = @DOC
        SET @PaidInstalment  = 0

        WHILE @SN2 <= @SNCounter2
        BEGIN
            SELECT @BonusStartDate = StartDate, @BonusEndDate = EndDate
            FROM #tmp_Policy_Bonus WHERE SNo = @SN2

            WHILE @ComingDueDate BETWEEN @BonusStartDate AND @BonusEndDate
            BEGIN
                SET @ComingDueDate = DATEADD(MM, @Duration, @ComingDueDate)
                IF @ComingDueDate NOT BETWEEN @BonusStartDate AND @BonusEndDate
                    BREAK
            END

            UPDATE #tmp_Policy_Bonus
            SET NoOfInstallment = @PaidInstalment,
                BonusYear       = @PaidInstalment * @Duration / 12.0
            WHERE SNo = @SN2

            SET @PaidInstalment = @PaidInstalment + 1
            SET @SN2            = @SN2 + 1
        END

        SET @SN = @SN + 1
    END

    UPDATE #tmp_Policy_Bonus
    SET TotalBonus = ISNULL(SA * BonusRate / 1000, 0)

    -- =========================================================
    -- 5. Push bonus totals back into #SurrenderCalculation
    --    and compute BonusAfterAdjustment — no #BonusGrouping
    --    temp table needed, done inline via CTE
    -- =========================================================
    ;WITH cte_BonusGrouped AS
    (
        SELECT RegisterNo, SUM(TotalBonus) AS TotalBonus
        FROM #tmp_Policy_Bonus
        GROUP BY RegisterNo
    )
    UPDATE sc
    SET sc.TotalBonus           = ISNULL(bg.TotalBonus, 0),
        sc.BonusAfterAdjustment = ISNULL(ROUND((bg.TotalBonus * sc.SurrenderFactor * sc.MAF) / 1000, 2), 0)
    FROM #SurrenderCalculation sc
    INNER JOIN cte_BonusGrouped bg ON bg.RegisterNo = sc.RegisterNo

    -- =========================================================
    -- 6. Loan check (inlined from the dropped view)
    -- =========================================================
    SELECT @HasActiveLoan = CASE
        WHEN EXISTS (
            SELECT 1
            FROM tblGrouppolicyloandetail l
            WHERE l.policyNO = @PolicyNo
              AND l.status IN ('active', 'approved', 'registered')
        )
        THEN 1 ELSE 0
    END

    -- =========================================================
    -- 7. Final output
    -- =========================================================
    SELECT
        SurrenderValue = ROUND(
            ISNULL(SUM(PaidupValueWithFactor), 0) +
            ISNULL(SUM(BonusAfterAdjustment),  0),
        0),
        HasActiveLoan  = @HasActiveLoan
    FROM #SurrenderCalculation

END
GO

-- --ORGINAL
-- EXEC proc_CalculateGroupMultipleSurrender
--     @PolicyNo = 'GE1016-232',
--     @ClaimDate = '2026-04-08'

-- --STOLEN
-- EXEC proc_copo_surrender_calculator
--     @PolicyNo = 'GE1016-232'
   



