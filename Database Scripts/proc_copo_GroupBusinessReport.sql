CREATE OR ALTER PROCEDURE proc_copo_BusinessDetail
    @GroupId    VARCHAR(50),
    @FromDate   DATE,
    @ToDate     DATE,
    @FilterBy   VARCHAR(10),    -- 'PaidDate' or 'ValueDate'
    @Flag       VARCHAR(5)      -- 'NB' or 'RB'
AS
BEGIN
    SET NOCOUNT ON;

    -- =====================
    -- VALIDATION
    -- =====================
    IF @Flag NOT IN ('NB', 'RB')
    BEGIN
        RAISERROR('Invalid @Flag. Use ''NB'' for New Business or ''RB'' for Renewal Business.', 16, 1);
        RETURN;
    END

    IF @FilterBy NOT IN ('PaidDate', 'ValueDate')
    BEGIN
        RAISERROR('Invalid @FilterBy. Use ''PaidDate'' or ''ValueDate''.', 16, 1);
        RETURN;
    END

    -- =====================
    -- NEW BUSINESS (NB)
    -- =====================
    IF @Flag = 'NB'
    BEGIN
        SELECT
            TB2.BranchName,
            tge.Name,
            B.RegisterNo,
            B.PolicyNo,
            B.GroupId,
            CAST(B.SumAssured AS INT)                       AS SA,
            CAST(B.Premium AS MONEY)                        AS Premium,
            B.Term,
            CONVERT(VARCHAR(10), B.DOC, 103)                AS DOC,
            CONVERT(VARCHAR(10), B.FUP, 103)                AS NextDueDate,
            CONVERT(VARCHAR(10), tge.DOB, 103)              AS DOB,
            CASE
                WHEN tge.Gender = '9'   THEN 'Male'
                WHEN tge.Gender = '10'  THEN 'Female'
                WHEN tge.Gender = '126' THEN 'Others'
                ELSE tge.Gender
            END                                             AS Gender,
            vapv.ValueDate,
            CONVERT(VARCHAR(10), vapv.ValueDate, 103)       AS ValueDate_Formatted,
            CONVERT(VARCHAR(10), B.MaturityDate, 103)       AS MaturityDate,
            vapv.PaidDate,
            CONVERT(VARCHAR(10), vapv.PaidDate, 103)        AS PaidDate_Formatted,
            pd.VoucherNo,
            -- Rider columns (NULL if not applicable)
            CASE WHEN tge.IsADB = 'Y' THEN 'ADB' ELSE NULL END AS RiderID,
            CAST(B.SumAssured AS INT)                       AS RiderSA,
            tge.ExtraPremium                                AS RiderPremium,
            -- Renewal-only columns as NULL for unified shape
            NULL                                            AS [Status],
            NULL                                            AS Instalment,
            NULL                                            AS RiderSA_Renewal,
            NULL                                            AS [Paid Date]

        FROM dbo.vwAccountPostingV2 AS vapv WITH (NOLOCK)

        INNER JOIN tblAccount                    AS E   WITH (NOLOCK) ON E.AccountNo   = vapv.AccountNo
        INNER JOIN dbo.tblGroupEndowmentTermPaid AS pd  WITH (NOLOCK) ON pd.VoucherNo  = vapv.VoucherNo
        INNER JOIN dbo.tblGroupEndowmentDetails  AS B   WITH (NOLOCK) ON pd.PolicyNo   = B.PolicyNo
                                                                      AND pd.RegisterNo = B.RegisterNo
        INNER JOIN dbo.tblGroupEndowment         AS tge WITH (NOLOCK) ON pd.RegisterNo = tge.RegisterNo
        INNER JOIN dbo.tblBranch                 AS TB2 WITH (NOLOCK) ON TB2.Branch    = pd.Branch

        WHERE
            vapv.GLCode          = '196'
            AND pd.InstalmenType = 'F'
            AND vapv.Amount      < 0
            AND B.GroupId        = @GroupId
            AND (
                (@FilterBy = 'ValueDate' AND CAST(vapv.ValueDate AS DATE) BETWEEN @FromDate AND @ToDate)
                OR
                (@FilterBy = 'PaidDate'  AND CAST(vapv.PaidDate  AS DATE) BETWEEN @FromDate AND @ToDate)
            );

        RETURN;
    END

    -- =====================
    -- RENEWAL BUSINESS (RB)
    -- =====================
    IF @Flag = 'RB'
    BEGIN
        SELECT
            TB2.BranchName,
            id.Name,
            pd.RegisterNo,
            pd.PolicyNo,
            pd.GroupId,
            CAST(pd.SumAssured AS INT)                          AS SA,
            CAST(tpp.Premium AS MONEY)                          AS Premium,
            pd.Term,
            CONVERT(VARCHAR(10), pd.DOC, 103)                   AS DOC,
            CONVERT(VARCHAR(10), pd.FUP, 103)                   AS NextDueDate,
            CONVERT(VARCHAR(10), id.DOB, 103)                   AS DOB,
            CASE
                WHEN id.Gender = '9'   THEN 'Male'
                WHEN id.Gender = '10'  THEN 'Female'
                WHEN id.Gender = '126' THEN 'Others'
                ELSE id.Gender
            END                                                 AS Gender,
            c.ValueDate,
            CONVERT(VARCHAR(10), c.ValueDate, 103)              AS ValueDate_Formatted,
            CONVERT(VARCHAR(10), pd.MaturityDate, 103)          AS MaturityDate,
            c.PaidDate,
            CONVERT(VARCHAR(10), c.PaidDate, 103)               AS PaidDate_Formatted,
            tpp.VoucherNo,
            -- Rider columns
            CASE WHEN id.IsADB = 'Y' THEN 'ADB' ELSE NULL END  AS RiderID,
            CAST(pd.SumAssured AS INT)                          AS RiderSA,
            id.ExtraPremium                                     AS RiderPremium,
            -- Renewal-only columns
            pd.PolicyStatus                                     AS [Status],
            pd.Instalment,
            NULL                                                AS RiderSA_Renewal,
            CONVERT(VARCHAR(10), c.PaidDate, 103)               AS [Paid Date]

        FROM vwAccountPostingv2 AS c WITH (NOLOCK)

        INNER JOIN tblAccount                    AS a   WITH (NOLOCK) ON a.AccountNo   = c.AccountNo
        INNER JOIN dbo.tblGroupEndowmentTermPaid AS tpp WITH (NOLOCK) ON tpp.VoucherNo = c.VoucherNo
        INNER JOIN dbo.tblGroupEndowmentDetails  AS pd  WITH (NOLOCK) ON pd.PolicyNo   = tpp.PolicyNo
                                                                      AND pd.RegisterNo = tpp.RegisterNo
        INNER JOIN dbo.tblGroupEndowment         AS id  WITH (NOLOCK) ON id.RegisterNo = pd.RegisterNo
        INNER JOIN dbo.tblBranch                 AS TB2 WITH (NOLOCK) ON TB2.Branch    = pd.Branch

        WHERE
            c.VoucherCode        = 'RP'
            AND c.IsReverse      IS NULL
            AND pd.Instalment    <> '1'
            AND c.Amount         < 0
            AND c.Narration      LIKE 'Renewal Group Endowment Income on%'
            AND pd.GroupId       = @GroupId
            AND (
                (@FilterBy = 'ValueDate' AND CAST(c.ValueDate AS DATE) BETWEEN @FromDate AND @ToDate)
                OR
                (@FilterBy = 'PaidDate'  AND CAST(c.PaidDate  AS DATE) BETWEEN @FromDate AND @ToDate)
            );

        RETURN;
    END

END;


-- New Business filtered by ValueDate
-- EXEC proc_copo_BusinessDetail
--     @GroupId  = '052',
--     @FromDate = '2024-07-16',
--     @ToDate   = '2025-07-16',
--     @FilterBy = 'ValueDate',
--     @Flag     = 'NB';

-- Renewal Business filtered by PaidDate
-- EXEC proc_copo_BusinessDetail
--     @GroupId  = '052',
--     @FromDate = '2024-07-16',
--     @ToDate   = '2025-07-16',
--     @FilterBy = 'PaidDate',
--     @Flag     = 'RB';