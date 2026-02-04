CREATE OR ALTER VIEW dbo.view_copo_groupInformation
AS
WITH AggregatedData AS (
    SELECT
        GroupId,
        COUNT(*) AS Total_members_count,
        COUNT(DISTINCT CASE WHEN PolicyStatus = 'A' THEN PolicyNo END) AS Total_active_policies,
        SUM(Premium) AS Total_Premium,
        SUM(SumAssured) AS Total_SA,
        COUNT(DISTINCT CASE WHEN PolicyStatus = 'D' THEN PolicyNo END) AS Death_Claim,
        COUNT(DISTINCT CASE WHEN PolicyStatus = 'S' THEN PolicyNo END) AS Surrender_Claim,
        COUNT(DISTINCT CASE WHEN PolicyStatus = 'M' THEN PolicyNo END) AS Maturity_Claim,
        COUNT(DISTINCT CASE WHEN PolicyStatus = 'I' THEN PolicyNo END) AS Transfer_Claim,
        COUNT(DISTINCT CASE WHEN PolicyStatus = 'T' THEN PolicyNo END) AS Terminate_Claim,
        COUNT(DISTINCT CASE WHEN PolicyStatus IN ('C','cancel') THEN PolicyNo END) AS Cancel_Claim
    FROM tblGroupEndowmentDetails
    GROUP BY GroupId
)
SELECT
    gi.GroupId,
    gi.GroupName,
    gi.GroupNameNepali,
    gi.isactive,
    ad.Total_members_count,
    ad.Total_active_policies,
    ad.Total_Premium,
    ad.Total_SA,
    ad.Death_Claim,
    ad.Surrender_Claim,
    ad.Maturity_Claim,
    ad.Transfer_Claim,
    ad.Terminate_Claim,
    ad.Cancel_Claim
FROM tblGroupInformation gi
LEFT JOIN AggregatedData ad
    ON gi.GroupId = ad.GroupId;
GO