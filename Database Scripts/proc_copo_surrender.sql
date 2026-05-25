SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

CREATE OR ALTER PROCEDURE [dbo].[proc_copo_surrender_calculator]
(
    @PolicyNo            VARCHAR(50),
    @ClaimDate           DATE         = NULL,   -- defaults to today
    @ReducedInstalment   INT          = NULL,
    @GroupIdList         VARCHAR(MAX) = NULL     -- comma-separated e.g. 'GE1001,GE1002'
)
AS
SET NOCOUNT ON
BEGIN

    -- Default ClaimDate to today if not supplied
    IF @ClaimDate IS NULL
        SET @ClaimDate = CAST(GETDATE() AS DATE)

    DECLARE @LastDueDate   DATE
    DECLARE @PayMode       CHAR(1) = 'Y'
    DECLARE @Duration      INT     = 12

    -- Scalar loop variables for the per-policy bonus loop
    DECLARE @SN INT, @SNCounter INT
    DECLARE @SN2 INT, @SNCounter2 INT
    DECLARE @SA MONEY, @DOC DATE, @FUP DATE, @RegisterNo VARCHAR(100)
    DECLARE @Fupforbonuscalculation DATE
    DECLARE @ComingDueDate  DATETIME
    DECLARE @PaidInstalment INT
    DECLARE @BonusStartDate DATETIME, @BonusEndDate DATETIME

    DECLARE @ReducedInstalmentUP INT

    -- =========================================================
    -- 1. Resolve GroupId list
    --    If caller passes nothing, derive from tblGroupEndowment
    --    exactly as the original procedure does
    -- =========================================================
    DECLARE @GroupIds TABLE (GroupId VARCHAR(50))

    IF @GroupIdList IS NULL OR LTRIM(RTRIM(@GroupIdList)) = ''
    BEGIN
        INSERT INTO @GroupIds (GroupId)
        SELECT TOP 1 GroupId
        FROM tblGroupEndowment
        WHERE PolicyNo = @PolicyNo
    END
    ELSE
    BEGIN
        -- Split comma-separated list sent from Django
        INSERT INTO @GroupIds (GroupId)
        SELECT LTRIM(RTRIM(value))
        FROM STRING_SPLIT(@GroupIdList, ',')
        WHERE LTRIM(RTRIM(value)) <> ''
    END

    -- =========================================================
    -- 2. #SurrenderCalculation
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

    -- Base insert — honours all GroupIds in the list
    INSERT INTO #SurrenderCalculation
        (PolicyNo, RegisterNo, SA, DOC, MaturityDate, ClaimDate, Term, FUP)
    SELECT
        ge.PolicyNo, ge.RegisterNo, ge.SumAssured,
        ge.DOC, ge.MaturityDate, @ClaimDate, g.Term, ge.FUP
    FROM tblGroupEndowmentDetails ge
    INNER JOIN tblGroupEndowment g
        ON  ge.PolicyNo   = g.PolicyNo
        AND ge.RegisterNo = g.RegisterNo
    WHERE ge.PolicyNo = @PolicyNo
      AND ge.GroupId IN (SELECT GroupId FROM @GroupIds)
    ORDER BY ge.DOC ASC

    -- PaidYear: mirrors original — ReducedInstalment rolls back FUP
    UPDATE #SurrenderCalculation
    SET PaidYear = CASE
                       WHEN @ReducedInstalment IS NOT NULL
                       THEN ROUND(DATEDIFF(MM, DOC,
                                  DATEADD(YEAR, -(1 * @ReducedInstalment), FUP)) / 12.0, 0)
                       ELSE ROUND(DATEDIFF(MM, DOC, FUP) / 12.0, 0)
                   END

    UPDATE #SurrenderCalculation
    SET PaidupValue = (SA * PaidYear) / NULLIF(Term, 0)

    -- RemainingPeriod: group-specific logic preserved from original
    UPDATE #SurrenderCalculation
    SET RemainingPeriod = CASE
                              WHEN EXISTS (
                                  SELECT 1 FROM @GroupIds g
                                  WHERE g.GroupId IN
                                      ('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
                              )
                              THEN (Term - PaidYear)
                              ELSE CAST(
                                  CONVERT(INT,
                                      dbo.FullMonthsSeparation(@ClaimDate, MaturityDate)
                                  ) / 12.0 AS INT)
                          END

    UPDATE sc
    SET sc.SurrenderFactor = sf.Factor
    FROM #SurrenderCalculation sc
    LEFT JOIN tblSurrenderFactor sf (NOLOCK)
        ON sf.PERIOD = FLOOR(sc.RemainingPeriod)

    -- SurrenderFactor adjustment: same group list as original
    UPDATE #SurrenderCalculation
    SET SurrenderFactor = CASE
                              WHEN EXISTS (
                                  SELECT 1 FROM @GroupIds g
                                  WHERE g.GroupId IN
                                      ('GE1001','GE1002','GE1003','GE1004','GE1005',
                                       'GE1006','GE1022')
                              )
                              THEN SurrenderFactor
                              ELSE SurrenderFactor
                          END
    -- Note: original kept the same value for both branches (the -5% was commented out).
    -- Preserving that behaviour; update this CASE if the discount is ever reinstated.

    -- AnniversaryDate
    UPDATE #SurrenderCalculation
    SET AnniversaryDate = CONVERT(DATETIME,
        CONVERT(VARCHAR, YEAR(@ClaimDate)) + '-' +
        CONVERT(VARCHAR, MONTH(DOC))       + '-' +
        CONVERT(VARCHAR, DAY(DOC)))

    UPDATE #SurrenderCalculation
    SET AnniversaryDate = CASE
                              WHEN AnniversaryDate > @ClaimDate
                              THEN DATEADD(MM, -12, AnniversaryDate)
                              ELSE AnniversaryDate
                          END
    WHERE @ClaimDate <= DATEADD(YEAR, -1, MaturityDate)

    UPDATE #SurrenderCalculation
    SET RemainingMonth = dbo.FullMonthsSeparation(AnniversaryDate, @ClaimDate)

    UPDATE #SurrenderCalculation
    SET MAF = 1 + RemainingMonth * 0.5 / 100

    UPDATE #SurrenderCalculation
    SET PaidupValueWithFactor = ROUND((PaidupValue * SurrenderFactor * MAF) / 1000, 2)

    -- =========================================================
    -- 3. LastDueDate — mirrors original ReducedInstalment logic
    -- =========================================================
    SELECT TOP 1 @LastDueDate = DATEADD(YEAR, -1, FUP)
    FROM #SurrenderCalculation

    IF @ReducedInstalment IS NOT NULL
    BEGIN
        SET @ReducedInstalmentUP = @ReducedInstalment + 1

        SELECT TOP 1 @LastDueDate = DATEADD(YEAR, -(1 * @ReducedInstalmentUP), FUP)
        FROM #SurrenderCalculation
    END

    -- =========================================================
    -- 4. Bonus calculation (unchanged from your version)
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

        ;WITH cte_FupSeries AS
        (
            SELECT CAST(@DOC AS DATE) AS FUP
            UNION ALL
            SELECT CAST(dbo.FN_AllNextFUPDate(FUP, @PayMode) AS DATE)
            FROM cte_FupSeries
            WHERE CAST(dbo.FN_AllNextFUPDate(FUP, @PayMode) AS DATE) < @FUP
        )
        INSERT INTO #tmp_Policy_Bonus (SNo, RegisterNo, StartDate, EndDate, BonusRate, SA)
        SELECT
            ROW_NUMBER() OVER (ORDER BY br.StartDate),
            @RegisterNo,
            CASE WHEN @DOC BETWEEN br.StartDate AND br.EndDate
                 THEN @DOC ELSE br.StartDate END,
            CASE WHEN @LastDueDate BETWEEN br.StartDate AND br.EndDate
                 THEN @LastDueDate ELSE br.EndDate END,
            br.[Percent],
            @SA
        FROM tblBonusRate br (NOLOCK)
        WHERE br.[PlanID] = 1
          AND @DOC        <= br.EndDate
          AND br.StartDate <= @LastDueDate
          AND EXISTS (
                SELECT 1 FROM cte_FupSeries f
                WHERE f.FUP BETWEEN br.StartDate AND br.EndDate
              )
        OPTION (MAXRECURSION 1000)

        DELETE FROM #tmp_Policy_Bonus WHERE EndDate > @LastDueDate

        SET @SN2 = 0
        SELECT @SNCounter2  = MAX(SNo) FROM #tmp_Policy_Bonus
        SET @ComingDueDate  = @DOC
        SET @PaidInstalment = 0

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
    -- 5. Push bonus totals into #SurrenderCalculation
    -- =========================================================
    ;WITH cte_BonusGrouped AS
    (
        SELECT RegisterNo, SUM(TotalBonus) AS TotalBonus
        FROM #tmp_Policy_Bonus
        GROUP BY RegisterNo
    )
    UPDATE sc
    SET sc.TotalBonus           = ISNULL(bg.TotalBonus, 0),
        sc.BonusAfterAdjustment = ISNULL(
            ROUND((bg.TotalBonus * sc.SurrenderFactor * sc.MAF) / 1000, 2), 0)
    FROM #SurrenderCalculation sc
    INNER JOIN cte_BonusGrouped bg ON bg.RegisterNo = sc.RegisterNo

    -- =========================================================
    -- 6. Loan
    -- =========================================================
    DECLARE @IntimationDate    DATE  = @ClaimDate
    DECLARE @TotalDaysFY       INT
    DECLARE @LnDate            DATETIME
    DECLARE @LoanAmount        MONEY
    DECLARE @AccrualInterest1  MONEY
    DECLARE @remainingInterest MONEY
    DECLARE @daysAccured       FLOAT
    DECLARE @timediff          FLOAT
    DECLARE @InterestonLoan    MONEY

    SELECT @TotalDaysFY = TotalDays
    FROM TblFiscalYear (NOLOCK)
    WHERE IsActive = 1

    SELECT @LnDate = ISNULL(lastpaiddate, LoanDate)
    FROM dbo.tblGroupPolicyLoanDetail (NOLOCK)
    WHERE PolicyNo = @PolicyNo
      AND ApprovedDate IS NOT NULL
      AND Status = 'ACTIVE'

    SELECT
        @LoanAmount        = PrincipalAmount + ISNULL(AccrualAmount, 0),
        @daysAccured       = DATEDIFF(dd, @LnDate, @IntimationDate),
        @remainingInterest = RemainingInterest,
        @AccrualInterest1  = ISNULL(AccrualAmount, 0)
    FROM dbo.tblGroupPolicyLoanDetail (NOLOCK)
    WHERE PolicyNo = @PolicyNo
      AND Status = 'ACTIVE'

    -- Use the same dedicated function as the original
    SELECT @InterestonLoan = fplic.TotalInterest
    FROM dbo.FN_GroupPolicyLoanInterestCalculation(@PolicyNo, @IntimationDate) AS fplic

    SET @InterestonLoan = ROUND(CASE WHEN @InterestonLoan > 0 THEN @InterestonLoan ELSE 0 END, 0)
    SET @LoanAmount     = ROUND(CASE WHEN @LoanAmount     > 0 THEN @LoanAmount     ELSE 0 END, 0)

    -- Strip accrual already baked into principal, add any remaining interest
    SELECT @LoanAmount      = ISNULL(@LoanAmount, 0) - ISNULL(@AccrualInterest1, 0)
    SET    @InterestonLoan  = @InterestonLoan + ISNULL(@remainingInterest, 0)

    -- =========================================================
    -- 7. Tax — post-tax net value as agreed
    -- =========================================================
    DECLARE @TotalPremiumPaid  MONEY
    DECLARE @PaidupValue       MONEY
    DECLARE @BonusAfterAdj     MONEY
    DECLARE @TaxAmount         MONEY
    DECLARE @Tax               MONEY
    DECLARE @ExcessLess        MONEY

    SELECT @TotalPremiumPaid = SUM(PaidAmount)
    FROM tblGroupEndowmentDetails
    WHERE PolicyNo = @PolicyNo
      AND GroupId IN (SELECT GroupId FROM @GroupIds)

    SELECT @PaidupValue  = SUM(PaidupValueWithFactor) FROM #SurrenderCalculation
    SELECT @BonusAfterAdj = SUM(BonusAfterAdjustment)  FROM #SurrenderCalculation

    SELECT @ExcessLess = Amount
    FROM dbo.tblGroupExcessLess (NOLOCK)
    WHERE PolicyNo = @PolicyNo

    SET @TaxAmount = ROUND(
        (ISNULL(@PaidupValue, 0) + ISNULL(@BonusAfterAdj, 0)) -
         ISNULL(@TotalPremiumPaid, 0), 0)

    IF @TaxAmount < 0
        SET @TaxAmount = 0

    SET @Tax = ROUND(CASE WHEN @TaxAmount > 0 THEN @TaxAmount * 0.05 ELSE 0 END, 0)

    -- =========================================================
    -- 8. Final output — surrender value (post-tax, after loan)
    -- =========================================================
    SELECT
        GrossSurrenderValue = ROUND(
            ISNULL(@PaidupValue,   0) +
            ISNULL(@BonusAfterAdj, 0), 0),

        Tax = ISNULL(@Tax, 0),

        NetSurrenderValue = ROUND(
            ISNULL(@PaidupValue,    0) +
            ISNULL(@BonusAfterAdj,  0) -
            ISNULL(@LoanAmount,     0) -
            ISNULL(@InterestonLoan, 0) +
            ISNULL(@ExcessLess,     0) -
            ISNULL(@Tax,            0), 0),

        LoanDeducted     = ISNULL(@LoanAmount,     0),
        LoanInterest     = ISNULL(@InterestonLoan, 0),
        ExcessLess       = ISNULL(@ExcessLess,     0),
        ClaimDate        = @ClaimDate

END
GO

-- --ORGINAL
-- EXEC proc_CalculateGroupMultipleSurrender
--     @PolicyNo = 'GE1016-232',
--     @ClaimDate = '2026-05-25'

-- -- --STOLEN
-- EXEC proc_copo_surrender_calculator
--     @PolicyNo = 'GE1016-232'
--     @ClaimDate = '2026-05-25'



