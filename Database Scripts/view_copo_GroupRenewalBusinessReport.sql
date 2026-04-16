CREATE OR ALTER VIEW view_copo_GroupBusinessReport AS

WITH GroupBusinessCTE AS (
    SELECT 
        TB2.BranchName,
        pd.RegisterNo,
        pd.PolicyNo,
        pd.GroupId,
        id.Name                                             AS [Policy Holder Name],
        CAST(tpp.Premium AS MONEY)                          AS [Premium],
        CAST(pd.SumAssured AS INT)                          AS [SA],
        CONVERT(VARCHAR(10), pd.DOC, 103)                   AS [DOC],
        c.ValueDate,                                        -- raw for filtering
        CONVERT(VARCHAR(10), c.ValueDate, 103)              AS [Receipt Date],
        CONVERT(VARCHAR(10), pd.FUP, 103)                   AS [NextDueDate],
        pd.MaturityDate,
        pd.Term,
        pd.PolicyStatus                                     AS [Status],
        c.VoucherNo,
        CASE WHEN id.IsADB = 'Y' THEN 'ADB' ELSE NULL END  AS RiderID,
        pd.SumAssured                                       AS RiderSA,
        id.ExtraPremium                                     AS RiderPremium,
        pd.Instalment,
        id.DOB,
        CASE 
        WHEN id.Gender = '9'   THEN 'Male'
        WHEN id.Gender = '10'  THEN 'Female'
        WHEN id.Gender = '126' THEN 'Others'
        ELSE id.Gender 
        END                                     AS Gender,
        c.PaidDate,                                         -- raw for filtering
        CONVERT(VARCHAR(10), c.PaidDate, 103)               AS [Paid Date]

    FROM vwAccountPostingv2 AS c WITH (NOLOCK)

    INNER JOIN tblAccount                    AS a   WITH (NOLOCK) ON a.AccountNo   = c.AccountNo
    INNER JOIN dbo.tblGroupEndowmentTermPaid AS tpp WITH (NOLOCK) ON tpp.VoucherNo = c.VoucherNo
    INNER JOIN dbo.tblGroupEndowmentDetails  AS pd  WITH (NOLOCK) ON pd.PolicyNo   = tpp.PolicyNo
                                                                  AND pd.RegisterNo = tpp.RegisterNo
    INNER JOIN dbo.tblGroupEndowment         AS id  WITH (NOLOCK) ON id.RegisterNo = pd.RegisterNo
    INNER JOIN dbo.tblBranch                 AS TB2 WITH (NOLOCK) ON TB2.Branch    = pd.Branch  

    WHERE
        c.VoucherCode = 'RP'
        AND c.IsReverse   IS NULL
        AND pd.Instalment <> '1'
        AND c.Amount       < 0
        AND c.Narration    LIKE 'Renewal Group Endowment Income on%'
)

SELECT * FROM GroupBusinessCTE;

-- SELECT * FROM view_copo_GroupBusinessReport
-- WHERE PaidDate BETWEEN '2024-07-16' AND '2025-07-16'
-- and groupId = '052';
-- select TOP 10 * from tblgroupendowmentdetails where policyNO = 'AFP16945' and RegisterNo = 'GE1005_AFP16945_2018-07-17'