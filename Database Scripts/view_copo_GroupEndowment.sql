SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE   VIEW [dbo].[view_copo_groupEndowment]
WITH SCHEMABINDING
AS
SELECT 
    -- Join Keys
    ge.Branch,
    ged.RegisterNo,
    ged.PolicyNo,
    
    -- Fields prioritizing tblGroupEndowmentDetails (more reliable)
    ged.GroupId as GroupId,
    ged.DOC as DOC,
    ged.Term as Term,
    ged.SumAssured as SumAssured,
    ged.Premium as Premium,
    ged.FUP as FUP,
    ged.MaturityDate as MaturityDate,
    ged.PolicyStatus as PolicyStatus,
    ged.PolicyType as PolicyType,
    ged.LateFine as LateFine,
    
    -- Fields unique to tblGroupEndowmentDetails
    ged.PaidDate,
    ged.Instalment,
    ged.PaidAmount,
    ged.BatchNo,
    ged.Remarks as DetailsRemarks,
    ged.Intrest,
    ged.ClaimStatus,
    ged.LateFinePercent,
    ged.ReducedInstalment,
    
    -- Fields unique to tblGroupEndowment
    ge.EmployeeId,
    ge.Name,
    ge.NepName,
    ge.Gender,
    ge.Occupation,
    ge.DOB,
    ge.Age,
    ge.ExtraPremium,
    ge.TotalPremium,
    ge.IdNo,
    ge.IdType,
    ge.AppointedDate,
    ge.Remarks as EndowmentRemarks,
    ge.Address,
    ge.Email,
    ge.Mobile,
    ge.ADB,
    ge.PreviousPolicy,
    ge.OccExtraAmount,
    ge.ADBDiscount,
    ge.FatherName,
    ge.MotherName,
    ge.NomineeName,
    ge.NomineeAddress,
    ge.PhoneNumberResidence,
    ge.TransferDate,
    ge.DuplicatePolicyDate,
    ge.ApprovedDate,
    ge.ApprovedBy,
    ge.LapseDate,
    ge.LapseActiveDate,
    ge.DOE,
    ge.ApproveRemarks,
    ge.ModifiedDate,
    ge.BasicPremium,
    ge.IsADB,
    ge.AfterDisRebateRate,
    ge.FiscalYear,
    ge.NomineeRelationship,
    ge.ClaimDate,
    ge.TerminationDate,
    ge.IsINDIssue,
    ge.ProvinceID,
    ge.DistrictID,
    ge.MunicipalityID,
    ge.WardNo,
    ge.AgeProofDocType,
    ge.AgeProofDocNo,
    ge.NepAddress,
    ge.NepFatherName,
    ge.NepMotherName,
    ge.NepNomineeName,
    ge.NepNomineeAddress,
    ge.NomDistrictID,
    ge.NomineeWardNo,
    ge.NomineePhone,
    ge.PlanId,
    ge.IsMultiplePolicyIssued,
    ge.TerminateBy,
    ge.CancelDate,
    ge.CancelBy,
    ge.ActiveDate,
    ge.ActiveBy,
    ge.TerminateRemarks,
    ge.CancelRemarks,
    ge.ActiveRemarks,
    ge.LapseBy,
    ge.LapseRemarks
    
FROM [dbo].[tblGroupEndowment] ge
INNER JOIN [dbo].[tblGroupEndowmentDetails] ged
    ON ge.RegisterNo = ged.RegisterNo 
    AND ge.PolicyNo = ged.PolicyNo;
GO
SET ARITHABORT ON
SET CONCAT_NULL_YIELDS_NULL ON
SET QUOTED_IDENTIFIER ON
SET ANSI_NULLS ON
SET ANSI_PADDING ON
SET ANSI_WARNINGS ON
SET NUMERIC_ROUNDABORT OFF
GO
CREATE UNIQUE CLUSTERED INDEX [IX_view_copo_groupEndowment] ON [dbo].[view_copo_groupEndowment]
(
	[RegisterNo] ASC,
	[PolicyNo] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, IGNORE_DUP_KEY = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
