CREATE OR ALTER VIEW view_copo_GroupNewBusinessReport AS

SELECT
    TB2.BranchName,
    tge.Name,
    B.RegisterNo,
    B.PolicyNo,
    B.GroupId,
    CAST(B.SumAssured AS INT)               AS SA,
    CAST(B.Premium AS MONEY)                AS Premium,
    B.Term,
    CONVERT(VARCHAR(10), B.DOC, 103)        AS DOC,
    CONVERT(VARCHAR(10), B.FUP, 103)        AS NextDueDate,
    CONVERT(VARCHAR(10), tge.DOB, 103)      AS DOB,
    tge.DOB                                 AS DOBRaw,          -- raw for filtering
    CASE 
        WHEN tge.Gender = '9'   THEN 'Male'
        WHEN tge.Gender = '10'  THEN 'Female'
        WHEN tge.Gender = '126' THEN 'Others'
        ELSE tge.Gender 
    END                                     AS Gender,
    vapv.ValueDate,                                             -- raw for filtering
    CONVERT(VARCHAR(10), vapv.ValueDate, 103) AS ValueDate_Formatted,
    CONVERT(VARCHAR(10), B.MaturityDate, 103) AS MaturityDate,
    vapv.PaidDate,                                              -- raw for filtering
    CONVERT(VARCHAR(10), vapv.PaidDate, 103)  AS PaidDate_Formatted,
    pd.VoucherNo
    -- E.AccountName

FROM dbo.vwAccountPostingV2 AS vapv WITH (NOLOCK)

INNER JOIN tblAccount                    AS E   WITH (NOLOCK) ON E.AccountNo    = vapv.AccountNo
INNER JOIN dbo.tblGroupEndowmentTermPaid AS pd  WITH (NOLOCK) ON pd.VoucherNo   = vapv.VoucherNo
INNER JOIN dbo.tblGroupEndowmentDetails  AS B   WITH (NOLOCK) ON pd.PolicyNo    = B.PolicyNo
                                                              AND pd.RegisterNo  = B.RegisterNo
INNER JOIN dbo.tblGroupEndowment         AS tge WITH (NOLOCK) ON pd.RegisterNo  = tge.RegisterNo
INNER JOIN dbo.tblBranch                 AS TB2 WITH (NOLOCK) ON TB2.Branch    = pd.Branch

WHERE
    vapv.GLCode       = '196'
    AND pd.InstalmenType  = 'F'
    AND vapv.Amount       < 0;


-- SELECT * FROM view_copo_GroupNewBusinessReport
-- WHERE PaidDate BETWEEN '2024-07-16' AND '2025-07-16'
-- and groupid = '052';