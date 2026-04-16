CREATE OR ALTER VIEW view_copo_policySummary
AS
SELECT 
    a.registerNo,
    a.PolicyNo,
    a.Branch,
    a.Name,
    a.NepName,
    a.GroupId,
    a.DOB,
    a.Gender,
    a.Address,
    a.Email,
    a.Mobile,
    a.FatherName,
    a.MotherName,
    a.NomineeName,
    a.NomineeRelationship,
    a.ClaimDate,
    a.DistrictID,
    a.WardNo,
    a.NomineePhone,
    a.NomineeAddress,
    COALESCE(s.Value, a.Occupation) AS Occupation,
    b.Sumassured,
    b.DOC,
    b.PaidDate,
    b.FUP,
    b.Term,
    b.Premium,
    b.Instalment,
    b.PaidAmount,
    b.maturitydate,
    b.PolicyStatus,
    b.PolicyType
FROM tblGroupEndowment AS a
INNER JOIN tblgroupEndowmentDetails AS b  
    ON a.PolicyNo = b.PolicyNo 
    AND a.registerNo = b.registerNo
LEFT JOIN tblStaticDataValue AS s
    ON TRY_CAST(a.Occupation AS INT) = s.Id;
