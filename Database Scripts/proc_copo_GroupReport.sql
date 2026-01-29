-- EXEC proc_GroupReport @flag='MaturityForecastingReport' ,@User = 'rayal.khatri',@GroupId  = '052',
-- @FromDate= '2026-01-15',@ToDate = '2027-03-17'


EXEC proc_copo_GroupReport @flag='MaturityForecastingReport' ,@User = 'rayal',@GroupId  = '052',
@FromDate= '2026-01-15',@ToDate = '2027-03-17'
 
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE OR ALTER PROC [dbo].[proc_copo_GroupReport]
(
@Flag VARCHAR(50),
@VoucherNo VARCHAR(50)=NULL,
@ChequeNo VARCHAR(50)=NULL,
@RowId BIGINT = NULL,
@User VARCHAR(50) =NULL,
@EmployeeId VARCHAR(50) = NULL,
@Name NVARCHAR(50) = NULL,
@NepName NVARCHAR(50)=NULL,
@DOB DATETIME=NULL,
@PayMode CHAR = NULL, 
@Term SMALLINT = NULL,
@SA MONEY = NULL,
@Premium MONEY = NULL,
@TotalPremium MONEY = NULL,
@Gender NVARCHAR(50) = NULL,
@IdType VARCHAR (50) = NULL,
@IdNo VARCHAR(50) = NULL,
@Occupation NVARCHAR(50) = NULL,
@Address NVARCHAR(50) = NULL,
@Email VARCHAR(200) = NULL,
@Mobile VARCHAR(200) = NULL,
@DOC DATETIME = NULL,
@AppointedDate DATETIME = NULL,
@ADB MONEY = NULL,
@ExtraPremium MONEY = NULL,
@OccExtraAmount MONEY = NULL,
@ADBDiscount MONEY = NULL,
@Discount MONEY = NULL,
@DiscountoverPaymode MONEY = NULL,
@Remarks NVARCHAR(200) = NULL,
@XML XML=NULL,
@ProposalNo BIGINT  = NULL,
@Search NVARCHAR(50) = NULL,
@BatchNo BIGINT=NULL,
@GroupId	VARCHAR(50) = NULL,
@Pagesize INT = 10,
@GroupName VARCHAR(50)=NULL,
@GroupNepName NVARCHAR(50)=NULL,
@DiscountRate MONEY=NULL,
@ShortName VARCHAR(50)=NULL,
@FiscalYear VARCHAR(50)=NULL,
@GroupType VARCHAR(50)=NULL,
@StartDate VARCHAR(10)=NULL,
@Age VARCHAR(50)=NULL,
 @EndDate	VARCHAR(10)	= NULL,
 @FatherName VARCHAR(50)= NULL,
@MotherName VARCHAR(50)= NULL,
@NomineeName VARCHAR(50)= NULL,
@NomineeAddress VARCHAR(50)= NULL,
@PhoneNumberResidence VARCHAR(50) =NULL,
@PolicyStatus VARCHAR(10) = NULL ,
@MaturityDate DATETIME=NULL,
@TransferDate DATETIME=NULL,
@PolicyNo VARCHAR(50)=NULL,
@Bonus MONEY = NULL,
@DuplicatePolicyDate DATETIME = NULL,

@CutOffDate DATETIME = NULL,


@FromDate DATETIME = NULL,
@ToDate DATETIME = NULL,

@ClaimAmount MONEY  = NULL,
@CollectionType VARCHAR(50)  = NULL,
@TotalBonus MONEY =NULL,
@AppointedDateFrom Datetime =NULL,
@AppointedDateTo DATETIME =NULL,
@SurrenderAmount MONEY = NULL,
@DisplayLength		INT						=	NULL,						
@DisplayStart		INT						=	NULL,
@SortCol			INT						=	NULL,	
@SortDir			NVARCHAR(10)			=	NULL,	
@RegisterNo			VARCHAR(10)				=	NULL,
@Action				NVARCHAR(255)			=	NULL,
@FirstRec			INT						=	NULL,
@LastRec			INT						=	NULL,
@DOCDateFrom DATE =NULL,
@DOCDateTo DATE =NULL,
@TransferDateFrom DATE =NULL,
@TransferDateTo DATE =NULL,
@TransferType VARCHAR(100)=NULL,

@MemberNoFrom VARCHAR(MAX) =NULL,
@MemberNoTo VARCHAR(MAX) =NULL,

@Instalment INT =NULL,

@DOCFrom DATE =NULL,
@DOCTo DATE =NULL,
@TerminationDateFrom DATE =NULL,
@TerminationDateTo DATE= NULL,

@Status VARCHAR(100)=NULL,
@TransactionDate DATETIME=NULL,
@IntiDateFrom DATE =NULL,
@IntiDateTo DATE =NULL,
@DateOption VARCHAR(100)=NULL
,@RegisterFromDate DATETIME= Null
,@RegisterToDate DateTime= Null
,@MaturityPaidFromDate DATETIME= NULL
,@MaturityPaidToDate DateTime= NULL
,@DeathPaidFromDate	DateTime =NUll
,@DeathPaidToDate	DateTime =NUll
)
WITH RECOMPILE

AS 
BEGIN





 IF @Flag = 'GroupPolicyReport'
BEGIN

--SELECT GroupId, TotalNetPremium = SUM(Premium) INTO #TZ1 
--FROM tblGroupEndowment WHERE GroupId =ISNULL(@GroupId,GroupId) 
--AND ApprovedDate IS NOT NULL 
--GROUP BY GroupId 

--SELECT i.*,g.*,b.*
--FROM dbo.tblGroupEndowment g (NOLOCK)
--INNER JOIN #TZ1 b on g.GroupId = b.GroupId
--INNER JOIN dbo.tblGroupInformation i (NOLOCK)
--ON g.GroupID = i.GroupId
--WHERE g.PolicyNo BETWEEN @StartDate AND @EndDate 
--AND ApprovedDate IS NOT NULL

SELECT PolicyNo,TotalNetPremium = SUM(Premium) INTO #TempGroupInd FROM tblGroupEndowment a(NOLOCK) 
	WHERE PolicyNo=@PolicyNo AND PolicyStatus='A'
	 
	GROUP BY PolicyNo 

 SELECT * INTO #TempGroupInd1  FROM tblGroupEndowment a (NOLOCK)  WHERE PolicyNo=@PolicyNo AND PolicyStatus='A'
	 

	SELECT a.*,b.*,c.* FROM #TempGroupInd a INNER JOIN #TempGroupInd1 b on a.PolicyNo=b.PolicyNo INNER JOIN tblGroupInformation c on b.GroupId=c.GroupId

	RETURN;
--	SELECT c.*, a.* ,b.*
--	FROM tblGroupEndowment a(NOLOCK) INNER JOIN  #TZ b ON a.GroupId = b.GroupId 
--INNER JOIN tblGroupInformation c ON c.GroupId = a.GroupId 
DROP TABLE #TempGroupInd
DROP TABLE #TempGroupInd1
END

ELSE IF @Flag='GroupTransferReport'
BEGIN


IF @TransferType = 'Rastasawak'
BEGIN



SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn','Rastasawak Transfer Report' As [Report Name],
CONVERT(VARCHAR(10),@TransferDateFrom,105) AS [Transfer Date From:],
CONVERT(VARCHAR(10),@TransferDateTo,105) AS [Transfer Date To:]
,@MemberNoFrom AS PolicyNoFrom,@MemberNoTo AS PolicyNoTo
INTO  #tempRastasawakSearchParameterInformation


	SELECT ROW_NUMBER() OVER(ORDER BY a.PolicyNo asc) AS [S No.] ,a.EmployeeId,
	PD.PolicyNo,PD.PreviousPolicy,a.GroupId,a.Name,
	a.NepName AS[Nepali Name],
	CONVERT(VARCHAR(10),a.DOB,103) AS [DOB],a.Age,CONVERT(VARCHAR(10),a.DOC,103) AS [DOC],a.SumAssured AS SA,
	CAST(a.Term AS VARCHAR(10)) Term ,BasicPremium=
	CASE WHEN ISNULL(D.RiderPremium,0)>1 THEN ISNULL(PD.Premium,0)-ISNULL(D.RiderPremium,0) ELSE a.Premium END ,ISNULL(D.RiderPremium,0) AS ADB,PD.Premium As Premium,
	PaidAmount=PD.TotalPremiumPaid,CONVERT(VARCHAR(10),a.MaturityDate,103) AS [Maturity Date],PD.Instalment,TransferDate=CONVERT(VARCHAR(10),a.TransferDate,103)
	INTO #TempRastasawakApprove
	  FROM tblGroupEndowment a WITH(NOLOCK)
	 
	
	INNER JOIN dbo.tblGroupEndowmentDetails c ON a.RegisterNo=c.RegisterNo and  a.PolicyNo=c.PolicyNo
	INNER JOIN dbo.tblPolicyDetail PD ON a.NewRegisterNo=PD.RegisterNo
	LEFT JOIN dbo.tblInsuredRiders D ON a.NewRegisterNo=d.RegisterNo
	WHERE a.GroupId IN('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
	
	--AND A.PolicyNo BETWEEN ISNULL(@MemberNoFrom,A.PolicyNo) AND ISNULL(@MemberNoTo,A.PolicyNo)
	
	AND a.TransferDate BETWEEN CAST( ISNULL(@TransferDateFrom,a.TransferDate) AS DATE) AND CAST(ISNULL(@TransferDateTo,A.TransferDate) AS DATE)

AND PD.Instalment=ISNULL(@Instalment,PD.Instalment)

	AND a.TransferDate IS NOT NULL

	ORDER BY PolicyNo ASC


	

	Select * INTO #TempRastasawakApprove1 From #TempRastasawakApprove 
	
	UNION ALL
	SELECT MAX([S No.]) + 1,'Total','','','','','','','','',SUM(SA),'',SUM(BasicPremium),SUM(ADB),SUM(Premium),SUM(PaidAmount),'','','' 
	FROM #TempRastasawakApprove 
	

	SELECT * FROM #TempRastasawakApprove1 ORDER BY [S No.]

	
	select * from  #tempRastasawakSearchParameterInformation
	DROP TABLE #TempRastasawakApprove
DROP TABLE #TempRastasawakApprove1

	RETURN;
END

ELSE IF @TransferType = 'Group'
BEGIN

SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn','Group Transfer Report' As [Report Name],
CONVERT(VARCHAR(10),@TransferDateFrom,105) AS [Transfer Date From:],
CONVERT(VARCHAR(10),@TransferDateTo,105) AS [Transfer Date To:]
,@MemberNoFrom AS PolicyNoFrom,@MemberNoTo AS PolicyNoTo
INTO  #tempTransferSearchParameterInformation



SELECT ROW_NUMBER() OVER(ORDER BY a.PolicyNo asc) AS [S No.] ,a.EmployeeId,
	PD.PolicyNo,PD.PreviousPolicy,a.GroupId,a.Name,
	a.NepName AS[Nepali Name],
	CONVERT(VARCHAR(10),a.DOB,103) AS [DOB],a.Age,CONVERT(VARCHAR(10),a.DOC,103) AS [DOC],a.SumAssured AS SA,
	CAST(a.Term AS VARCHAR(10)) Term ,BasicPremium=
	CASE WHEN ISNULL(D.RiderPremium,0)>1 THEN ISNULL(PD.Premium,0)-ISNULL(D.RiderPremium,0) ELSE a.Premium END ,ISNULL(D.RiderPremium,0) AS ADB,PD.Premium As Premium,
	PaidAmount=PD.TotalPremiumPaid,CONVERT(VARCHAR(10),a.MaturityDate,103) AS [Maturity Date],PD.Instalment,TransferDate=CONVERT(VARCHAR(10),a.TransferDate,103)
	INTO #TempGroupTransferApprove
	  FROM tblGroupEndowment a WITH(NOLOCK)

	 
	
	INNER JOIN dbo.tblGroupEndowmentDetails c ON a.RegisterNo=c.RegisterNo and  a.PolicyNo=c.PolicyNo
	INNER JOIN dbo.tblPolicyDetail PD ON a.NewRegisterNo=PD.RegisterNo
	LEFT JOIN dbo.tblInsuredRiders D ON a.NewRegisterNo=d.RegisterNo
	WHERE a.GroupId NOT IN('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
	
	--AND A.PolicyNo BETWEEN ISNULL(@MemberNoFrom,A.PolicyNo) AND ISNULL(@MemberNoTo,A.PolicyNo)
	
	AND a.TransferDate BETWEEN CAST( ISNULL(@TransferDateFrom,a.TransferDate) AS DATE) AND CAST(ISNULL(@TransferDateTo,A.TransferDate) AS DATE)

	AND PD.Instalment=ISNULL(@Instalment,PD.Instalment)

	AND a.TransferDate IS NOT NULL

	ORDER BY PolicyNo ASC


	Select * INTO #TempGroupTransferApprove1 From #TempGroupTransferApprove 
	UNION ALL
	SELECT MAX([S No.]) + 1,'Total','','','','','','','','',SUM(SA),'',SUM(BasicPremium),SUM(ADB),SUM(Premium),SUM(PaidAmount),'','','' 
	FROM #TempGroupTransferApprove 
	

	SELECT * FROM #TempGroupTransferApprove1 ORDER BY [S No.]

	
	select * from  #tempTransferSearchParameterInformation
	DROP TABLE #TempGroupTransferApprove
DROP TABLE #TempGroupTransferApprove1

	RETURN;


END

ELSE
BEGIN 
SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn','All Group Transfer Report' As [Report Name],
CONVERT(VARCHAR(10),@TransferDateFrom,105) AS [Transfer Date From:],
CONVERT(VARCHAR(10),@TransferDateTo,105) AS [Transfer Date To:]
,@MemberNoFrom AS PolicyNoFrom,@MemberNoTo AS PolicyNoTo
INTO  #tempTransferAllSearchParameterInformation


	SELECT ROW_NUMBER() OVER(ORDER BY a.PolicyNo asc) AS [S No.] ,
	a.PolicyNo,a.Name,
	a.NepName AS[Nepali Name],
	CONVERT(VARCHAR(10),a.DOB,103) AS [DOB],CONVERT(VARCHAR(10),a.DOC,103) AS [DOC],a.SumAssured AS SA,
	CAST(a.Term AS VARCHAR(10)) Term ,BasicPremium=
	CASE WHEN ISNULL(a.BasicPremium,0)>1 THEN a.BasicPremium ELSE a.Premium END ,ISNULL(a.ExtraPremium,0) AS ADB,a.Premium As Premium,
	c.PaidAmount,CONVERT(VARCHAR(10),a.MaturityDate,103) AS [Maturity Date],c.Instalment,a.PreviousPolicy
	INTO #TempGroupTransferAllApprove
	  FROM tblGroupEndowment a WITH(NOLOCK)
	  INNER JOIN tblGroupEndowmentHistory b ON a.PreviousPolicy=b.PolicyNo
	
	INNER JOIN dbo.tblGroupEndowmentDetails c ON a.PolicyNo=c.PolicyNo
	WHERE b.GroupId =b.GroupId
	
	AND A.PolicyNo BETWEEN ISNULL(@MemberNoFrom,A.PolicyNo) AND ISNULL(@MemberNoTo,A.PolicyNo)
	
	AND a.TransferDate BETWEEN CAST( ISNULL(@TransferDateFrom,a.TransferDate) AS DATE) AND CAST(ISNULL(@TransferDateTo,A.TransferDate) AS DATE)

	AND c.Instalment=ISNULL(@Instalment,c.Instalment)

	AND a.TransferDate IS NOT NULL

	ORDER BY PolicyNo ASC

	

	Select * INTO #TempGroupTransferAllApprove1 From #TempGroupTransferAllApprove 
	
	UNION ALL
	SELECT MAX([S No.]) + 1,'Total','','','','',SUM(SA),'',SUM(BasicPremium),SUM(ADB),SUM(Premium),SUM(PaidAmount),'','','' 
	FROM #TempGroupTransferAllApprove 
	

	SELECT * FROM #TempGroupTransferAllApprove1 ORDER BY [S No.]

	
	select * from  #tempTransferAllSearchParameterInformation
	DROP TABLE #TempGroupTransferAllApprove
DROP TABLE #TempGroupTransferAllApprove1

	RETURN;
END



END

ELSE IF @Flag='MultiplePolicy'
BEGIN
--SELECT 'A'
--Author= Saroj Rai
--Last Updated 2021-08-17

CREATE TABLE #MultiplePolicyGroup(
	RowNum BIGINT NULL ,
	SN VARCHAR(100) NULL ,
	SubTotal VARCHAR(50) NULL,
	SubSeq INT NULL,
	PolicyNo VARCHAR(50) NULL,
		RegisterNo VARCHAR(50) NULL,
	EmployeeID varchar(50) NULL,
	Name NVARCHAR(50) NULL,
	NepName NVARCHAR(50) NULL,
	DOC DATE NULL,
	DOB DATE NULL,
	MaturityDate DATE NULL,
	Age INT NULL,
	Term INT NULL,
	SumAssured MONEY NULL,
	BasicPremium MONEY NULL,
	ADB MONEY NULL,
	OccExtraAmount MONEY NULL,
	ModeExtra MONEY NULL,
	Premium MONEY NULL,
	FUP DATE NULL,
	PaidAmount MONEY NULL,
	Instalment INT NULL,
	GroupId VARCHAR(50) NULL,
	Status VARCHAR(50) NULL,
	GroupName VARCHAR(100) NULL,
	SortIndex INT NULL,
	SortIndex2 INT NULL,
	LateFine MONEY NULL,
	LateFineRate MONEY NULL,
	DayCount MONEY NULL
	
	)
	IF @PolicyStatus='A'
	BEGIN
	INSERT INTO #MultiplePolicyGroup(RowNum,SubSeq,PolicyNo,RegisterNo,EmployeeID,Name,NepName,DOC,DOB,MaturityDate,Age,Term,SumAssured,BasicPremium,ADB,OccExtraAmount,ModeExtra,Premium,PaidAmount,FUP,Instalment,GroupId,Status,GroupName,SortIndex)
	SELECT ROW_NUMBER() OVER (ORDER BY a.PolicyNo), '1',a.PolicyNo,a.RegisterNo,a.EmployeeId,a.Name,a.NepName,a.DOC,a.DOB,a.MaturityDate,a.Age,a.Term,a.SumAssured,ISNULL(a.BasicPremium,0),ISNULL(a.ExtraPremium,0),ISNULL(a.EXT_PREMIUM,0),0 ,b.Premium,b.PaidAmount,b.FUP,b.Instalment,c.GroupId,a.PolicyStatus,c.GroupName,
	CAST(SUBSTRING(STUFF(a.PolicyNo, 1, PATINDEX('%[-]%', a.PolicyNo), ''),3,LEN(a.PolicyNo) ) AS BIGINT) AS SortIndex
	FROM tblGroupEndowment(NOLOCK) a INNER JOIN tblGroupEndowmentDetails (NOLOCK) b 
	ON A.PolicyNo=B.PolicyNo INNER JOIN tblGroupInformation (NOLOCK) c
	ON a.GroupId=c.GroupId
	WHERE  a.GroupId=ISNULL(@GroupId,a.GroupId)
	--AND a.Premium=b.Premium
	AND A.RegisterNo=B.RegisterNo
	AND a.PolicyNo=ISNULL(@PolicyNo,b.PolicyNo)
	AND a.DOC=ISNULL(@DOC,a.DOC)
	AND a.PolicyStatus  in('A','L')

	--RETURN
UPDATE #MultiplePolicyGroup SET DayCount =DATEDIFF(DAY,FUP,GETDATE())
UPDATE #MultiplePolicyGroup SET LateFine =0 WHERE DayCount <=30
UPDATE #MultiplePolicyGroup SET LateFine =5 WHERE DayCount  BETWEEN 30 AND 45

UPDATE #MultiplePolicyGroup SET LateFineRate = (SELECT isnull(Rate,0) from latefeerate where DayCount between StartDays and EndDays) WHERE DayCount >45
UPDATE #MultiplePolicyGroup set LateFine= ROUND((premium*(DayCount/365.00)*LateFineRate)/100.00,0) WHERE DayCount >45



	END
	ELSE
	BEGIN
	INSERT INTO #MultiplePolicyGroup(RowNum,SubSeq,PolicyNo,RegisterNo,EmployeeID,Name,NepName,DOC,DOB,MaturityDate,Age,Term,SumAssured,BasicPremium,ADB,OccExtraAmount,ModeExtra,Premium,PaidAmount,Instalment,GroupId,Status,GroupName,SortIndex)
	SELECT ROW_NUMBER() OVER (ORDER BY a.PolicyNo), '1',a.PolicyNo,a.RegisterNo,a.EmployeeId,a.Name,a.NepName,a.DOC,a.DOB,a.MaturityDate,a.Age,a.Term,a.SumAssured,ISNULL(a.BasicPremium,0),ISNULL(a.ExtraPremium,0),ISNULL(a.EXT_PREMIUM,0),0 
	,b.Premium,b.PaidAmount,b.Instalment,c.GroupId,a.PolicyStatus,c.GroupName,
	CAST(SUBSTRING(STUFF(a.PolicyNo, 1, PATINDEX('%[-]%', a.PolicyNo), ''),3,LEN(a.PolicyNo) ) AS BIGINT) AS SortIndex
	FROM tblGroupEndowment(NOLOCK) a INNER JOIN tblGroupEndowmentDetails (NOLOCK) b 
	ON A.PolicyNo=B.PolicyNo INNER JOIN tblGroupInformation (NOLOCK) c
	ON a.GroupId=c.GroupId
	WHERE  a.GroupId=ISNULL(@GroupId,a.GroupId)
	--AND a.Premium=b.Premium
	AND A.RegisterNo=B.RegisterNo
	AND a.PolicyNo=ISNULL(@PolicyNo,b.PolicyNo)
	AND a.DOC=ISNULL(@DOC,a.DOC)
	AND a.PolicyStatus  IN ('T','Terminate','D','S','M','I')

	
	
	END

	INSERT INTO #MultiplePolicyGroup(SubTotal,SubSeq,PolicyNo,SumAssured,BasicPremium,ADB,OccExtraAmount,ModeExtra,Premium,PaidAmount,LateFine)
	SELECT 'SubTotal',2,PolicyNo,SUM(SumAssured),SUM(BasicPremium),SUM(ADB),SUM(OccExtraAmount),SUM(ModeExtra),SUM(Premium),SUM(PaidAmount),SUM(LateFine) FROM #MultiplePolicyGroup (NOLOCK)
	GROUP BY PolicyNo

	UPDATE #MultiplePolicyGroup SET SN=SortIndex WHERE SubTotal IS NULL
	UPDATE #MultiplePolicyGroup SET SubTotal=0 WHERE SubTotal IS NULL

ALTER TABLE #MultiplePolicyGroup
ALTER COLUMN SubSeq VARCHAR(10);
ALTER TABLE #MultiplePolicyGroup
ALTER COLUMN Term VARCHAR(10);
ALTER TABLE #MultiplePolicyGroup
ALTER COLUMN Age VARCHAR(10);
--RETURN
	SELECT  SubTotal,SubSeq,SN,PolicyNo,RegisterNo,EmployeeId,Name,NepName,DOC,DOB,MaturityDate,Age,Term,SumAssured,BasicPremium,ADB,OccExtraAmount,ModeExtra,Premium,PaidAmount,Instalment,GroupId,Status,GroupName,LateFine,
	CAST(SUBSTRING(STUFF(PolicyNo, 1, PATINDEX('%[-]%', PolicyNo), ''),3,LEN(PolicyNo) ) AS BIGINT) AS SortIndex2 INTO #AAGroup FROM #MultiplePolicyGroup
	
	SELECT * INTO #BBGroup FROM #AAGroup (NOLOCK)
	UNION ALL SELECT 'GrandTotal','','','','','','','',null,null,null,'','',SUM(SumAssured),SUM(BasicPremium),SUM(ADB),SUM(OccExtraAmount),SUM(ModeExtra),SUM(Premium),SUM(PaidAmount),null,'','','',SUM(LateFine),MAX(SortIndex2+1) 
	FROM #AAGroup (NOLOCK) WHERE SubTotal='SubTotal'
	ORDER BY SortIndex2 ASC,PolicyNo ASC,SubSeq ASC,DOC ASC 

	SELECT ROW_NUMBER() OVER (ORDER BY SortIndex2 ASC) AS RowNum,PolicyNo 
	INTO #AAGroupSequence FROM #AAGroup (NOLOCK) GROUP BY PolicyNo,SortIndex2
	
	DECLARE @DueDate DATE

	SELECT TOP 1 @DueDate=FUP FROM dbo.tblGroupEndowmentDetails (NOLOCK) WHERE GroupId=@GroupId AND PolicyStatus=@PolicyStatus

	SELECT SubTotal,SubSeq,B.RowNum,SN,A.PolicyNo,RegisterNo,EmployeeId,Name,NepName,DOC,DOB,MaturityDate,Age,Term,SumAssured,BasicPremium,ADB,OccExtraAmount,ModeExtra,Premium,PaidAmount,LateFine,Total=Premium+LateFine,Instalment,GroupId,GroupName,FiscalYear=dbo.fn_GetFYPrefix(),A.Status AS PolicyStatus,DueDate=@DueDate
	 FROM  #BBGroup (NOLOCK) A LEFT JOIN #AAGroupSequence (NOLOCK) B ON A.PolicyNo=B.PolicyNo
	 ORDER BY SortIndex2 ASC,B.RowNum ASC,PolicyNo ASC,SubSeq ASC,DOC ASC 

DROP TABLE #BBGroup
DROP TABLE #AAGroupSequence
DROP TABLE #MultiplePolicyGroup
DROP TABLE #AAGroup
RETURN;
END

ELSE IF @Flag='TerminatePolicy'
BEGIN
IF @GroupId IN ('GE1001','GE1002','GE1003','GE1003','GE1004','GE1005','GE1022')
BEGIN
CREATE TABLE #MultipleTerminatePolicy(
	
	RowNum BIGINT NULL ,
	SN VARCHAR(100) NULL ,
	SubTotal VARCHAR(50) NULL,
	SubSeq INT NULL,
	PolicyNo VARCHAR(50) NULL,
	EmployeeID varchar(50) NULL,
	Name NVARCHAR(50) NULL,
	NepName NVARCHAR(50) NULL,
	DOC DATE NULL,
	DOB DATE NULL,
	MaturityDate DATE NULL,
	Age INT NULL,
	Term INT NULL,
	SumAssured MONEY NULL,
	BasicPremium MONEY NULL,
	ADB MONEY NULL,
	OccExtraAmount MONEY NULL,
	ModeExtra MONEY NULL,
	Premium MONEY NULL,
	PaidAmount MONEY NULL,
	Instalment INT NULL,
	GroupId VARCHAR(50) NULL,
	GroupName VARCHAR(100) NULL,
	SortIndex INT NULL,
	SortIndex2 INT NULL
	)

	INSERT INTO #MultipleTerminatePolicy(RowNum,SubSeq,PolicyNo,EmployeeID,Name,NepName,DOC,DOB,MaturityDate,Age,Term,SumAssured,BasicPremium,ADB,OccExtraAmount,ModeExtra,Premium,PaidAmount,Instalment,GroupId,GroupName,SortIndex)
	SELECT ROW_NUMBER() OVER (ORDER BY(SELECT NULL)),'1',a.PolicyNo,a.EmployeeId,a.Name,a.NepName,a.DOC,a.DOB,a.MaturityDate,a.Age,a.Term,a.SumAssured,a.BasicPremium,ISNULL(a.ExtraPremium,0),ISNULL(a.OccExtraAmount,0),0 ,b.Premium,b.PaidAmount,b.Instalment,c.GroupId,c.GroupName,
	CAST(STUFF(a.PolicyNo, 1, PATINDEX('%[0-9]%', a.PolicyNo)-1, '') AS BIGINT) AS SortIndex
	FROM tblGroupEndowment a INNER JOIN tblGroupEndowmentDetails b 
	ON A.PolicyNo=B.PolicyNo INNER JOIN tblGroupInformation c
	ON a.GroupId=c.GroupId
	WHERE  a.GroupId=ISNULL(@GroupId,a.GroupId)
	AND a.Premium=b.Premium
	AND A.RegisterNo=B.RegisterNo
	AND a.PolicyNo=ISNULL(@PolicyNo,b.PolicyNo)
	--AND a.DOC=ISNULL(@DOC,a.DOC)
	--change made for Doc
	AND a.DOC BETWEEN ISNULL(@DOCDateFrom,a.DOC) AND ISNULL(@DOCDateTo,A.DOC)
	--AND a.PolicyStatus Not in('A')
	AND a.PolicyStatus IN ('T')
	---added terminationdate
	AND a.TerminationDate BETWEEN ISNULL(@TerminationDateFrom,a.TerminationDate) AND ISNULL(@TerminationDateTo,a.TerminationDate)
    


	INSERT INTO #MultipleTerminatePolicy(SubTotal,SubSeq,PolicyNo,SumAssured,BasicPremium,ADB,OccExtraAmount,ModeExtra,Premium,PaidAmount)
	SELECT 'SubTotal',2,PolicyNo,SUM(SumAssured),SUM(BasicPremium),SUM(ADB),SUM(OccExtraAmount),SUM(ModeExtra),SUM(Premium),SUM(PaidAmount) FROM #MultipleTerminatePolicy
	GROUP BY PolicyNo

	UPDATE #MultipleTerminatePolicy SET SN=SortIndex WHERE SubTotal IS NULL
	UPDATE #MultipleTerminatePolicy SET SubTotal=0 WHERE SubTotal IS NULL

ALTER TABLE #MultipleTerminatePolicy
ALTER COLUMN SubSeq VARCHAR(10);
ALTER TABLE #MultipleTerminatePolicy
ALTER COLUMN Term VARCHAR(10);
ALTER TABLE #MultipleTerminatePolicy
ALTER COLUMN Age VARCHAR(10);
	
	SELECT  SubTotal,SubSeq,SN,PolicyNo,EmployeeId,Name,NepName,DOC,DOB,MaturityDate,Age,Term,SumAssured,BasicPremium,ADB,OccExtraAmount,ModeExtra,Premium,PaidAmount,Instalment,GroupId,GroupName,
	CAST(STUFF(PolicyNo, 1, PATINDEX('%[0-9]%', PolicyNo)-1, '') AS BIGINT) AS SortIndex2 INTO #AATerminate FROM #MultipleTerminatePolicy
	
	SELECT * FROM #AATerminate
	UNION ALL SELECT 'GrandTotal','','','','','','',null,null,null,'','',SUM(SumAssured),SUM(BasicPremium),SUM(ADB),SUM(OccExtraAmount),SUM(ModeExtra),SUM(Premium),SUM(PaidAmount),null,'','',MAX(SortIndex2+1) 
	FROM #AATerminate WHERE SubTotal='SubTotal'
	ORDER BY SortIndex2 ASC,PolicyNo ASC,SubSeq ASC,Term DESC 

	DROP TABLE #MultipleTerminatePolicy
	DROP TABLE #AATerminate
		
RETURN;
END
ELSE
BEGIN
CREATE TABLE #MultipleTerminatePolicyGroup(
	RowNum BIGINT NULL ,
	SN VARCHAR(100) NULL ,
	SubTotal VARCHAR(50) NULL,
	SubSeq INT NULL,
	PolicyNo VARCHAR(50) NULL,
		RegisterNo VARCHAR(50) NULL,
	EmployeeID varchar(50) NULL,
	Name NVARCHAR(50) NULL,
	NepName NVARCHAR(50) NULL,
	DOC DATE NULL,
	DOB DATE NULL,
	MaturityDate DATE NULL,
	Age INT NULL,
	Term INT NULL,
	SumAssured MONEY NULL,
	BasicPremium MONEY NULL,
	ADB MONEY NULL,
	OccExtraAmount MONEY NULL,
	ModeExtra MONEY NULL,
	Premium MONEY NULL,
	PaidAmount MONEY NULL,
	Instalment INT NULL,
	GroupId VARCHAR(50) NULL,
	Status VARCHAR(50) NULL,
	GroupName VARCHAR(100) NULL,
	TerminationDate Date NULL,
	TerminateBy VARCHAR(20) NULL,
	SortIndex INT NULL,
	SortIndex2 INT NULL
	
	)

	
	INSERT INTO #MultipleTerminatePolicyGroup(RowNum,SubSeq,PolicyNo,RegisterNo,EmployeeID,Name,NepName,DOC,DOB,MaturityDate,Age,Term,SumAssured,BasicPremium,ADB,OccExtraAmount,ModeExtra,Premium,PaidAmount,
	Instalment,GroupId,Status,
	GroupName,TerminationDate,TerminateBy,SortIndex)
	SELECT ROW_NUMBER() OVER (ORDER BY a.PolicyNo), '1',a.PolicyNo,a.RegisterNo,a.EmployeeId,a.Name,a.NepName,a.DOC,a.DOB,a.MaturityDate,a.Age,a.Term,a.SumAssured,ISNULL(a.BasicPremium,0),ISNULL(a.ExtraPremium,0),ISNULL(a.EXT_PREMIUM,0),0 ,b.Premium,b.PaidAmount,
	b.Instalment,c.GroupId,a.PolicyStatus,c.GroupName,a.TerminationDate,a.TerminateBy,
	CAST(STUFF(a.PolicyNo, 1, PATINDEX('%[-]%', a.PolicyNo), '') AS BIGINT) AS SortIndex
	FROM tblGroupEndowment a INNER JOIN tblGroupEndowmentDetails b 
	ON A.PolicyNo=B.PolicyNo INNER JOIN tblGroupInformation c
	ON a.GroupId=c.GroupId
	WHERE  a.GroupId=ISNULL(@GroupId,a.GroupId)
	AND a.Premium=b.Premium
	AND A.RegisterNo=B.RegisterNo
	AND a.PolicyNo=ISNULL(@PolicyNo,b.PolicyNo)
	AND a.DOC BETWEEN ISNULL(@DOCDateFrom,a.DOC) AND ISNULL(@DOCDateTo,A.DOC)
	AND a.TerminationDate BETWEEN ISNULL(@TerminationDateFrom,a.TerminationDate) AND ISNULL(@TerminationDateTo,a.TerminationDate)
	--AND a.PolicyStatus  NOT in('A')
	AND a.PolicyStatus IN ('T')

	
	
	
	
	
	INSERT INTO #MultipleTerminatePolicyGroup(SubTotal,SubSeq,PolicyNo,SumAssured,BasicPremium,ADB,OccExtraAmount,ModeExtra,Premium,PaidAmount)
	SELECT 'SubTotal',2,PolicyNo,SUM(SumAssured),SUM(BasicPremium),SUM(ADB),SUM(OccExtraAmount),SUM(ModeExtra),SUM(Premium),SUM(PaidAmount) FROM #MultipleTerminatePolicyGroup
	GROUP BY PolicyNo
	
	
	UPDATE #MultipleTerminatePolicyGroup SET SN=SortIndex WHERE SubTotal IS NULL
	UPDATE #MultipleTerminatePolicyGroup SET SubTotal=0 WHERE SubTotal IS NULL



ALTER TABLE #MultipleTerminatePolicyGroup
ALTER COLUMN SubSeq VARCHAR(10);
ALTER TABLE #MultipleTerminatePolicyGroup
ALTER COLUMN Term VARCHAR(10);
ALTER TABLE #MultipleTerminatePolicyGroup
ALTER COLUMN Age VARCHAR(10);




	
	SELECT  SubTotal,SubSeq,SN,PolicyNo,RegisterNo,EmployeeId,Name,NepName,DOC,DOB,MaturityDate,Age,Term,SumAssured,BasicPremium,ADB,OccExtraAmount,ModeExtra,Premium,PaidAmount,Instalment,GroupId,Status,GroupName,TerminationDate,TerminateBy,
	CAST(STUFF(PolicyNo, 1, PATINDEX('%[-]%', PolicyNo), '') AS BIGINT) AS SortIndex2 INTO #AATerminateGroup FROM #MultipleTerminatePolicyGroup
	
	SELECT * INTO #BBTerminateGroup FROM #AATerminateGroup
	UNION ALL SELECT 'GrandTotal','','','','','','','',null,null,null,'','',SUM(SumAssured),SUM(BasicPremium),SUM(ADB),SUM(OccExtraAmount),SUM(ModeExtra),SUM(Premium),SUM(PaidAmount),null,'','','','','',MAX(SortIndex2+1) 
	FROM #AATerminateGroup WHERE SubTotal='SubTotal'
	ORDER BY SortIndex2 ASC,PolicyNo ASC,SubSeq ASC,DOC ASC 





	SELECT ROW_NUMBER() OVER (ORDER BY SortIndex2 ASC) AS RowNum,PolicyNo 
	INTO #AATerminateGroupSequence FROM #AATerminateGroup GROUP BY PolicyNo,SortIndex2
	
	


	

	



	SELECT SubTotal,SubSeq,B.RowNum,SN,A.PolicyNo,RegisterNo,EmployeeId,Name,NepName,DOC,DOB,MaturityDate,Age,Term,SumAssured,BasicPremium,ADB,OccExtraAmount,ModeExtra,Premium,PaidAmount,Instalment,GroupId,GroupName,FiscalYear=dbo.fn_GetFYPrefix(),A.Status AS PolicyStatus,DueDate='',TerminationDate,TerminateBy
	 FROM  #BBTerminateGroup A LEFT JOIN #AATerminateGroupSequence B ON A.PolicyNo=B.PolicyNo
	 ORDER BY SortIndex2 ASC,B.RowNum ASC,PolicyNo ASC,SubSeq ASC,DOC ASC 







	 DROP TABLE #BBTerminateGroup



	DROP TABLE #MultipleTerminatePolicyGroup
	DROP TABLE #AATerminateGroup

		
RETURN;
END


END

ELSE IF @Flag='GroupAllReport'
BEGIN

IF @PolicyStatus IN ('A') AND @GroupId IN ('GE1001','GE1002','GE1003','GE1003','GE1004','GE1005','GE1022')
BEGIN

	SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupName As [Group Name], @FiscalYear AS [Fiscal Year],
CONVERT(VARCHAR(10),@GroupId,105) AS [Group Master Policy:],
CONVERT(VARCHAR(10),@Age,105) AS [Age:],CONVERT(VARCHAR(10),@DOCDateFrom,105) AS [DOC Date From:],
CONVERT(VARCHAR(10),@DOCDateTo,105) AS [DOC Date To:]
,@MemberNoFrom AS MemberNoFrom,@MemberNoTo AS MemberNoTo
INTO  #tempSearchParameterInformation



SELECT @MemberNoFrom=CAST(STUFF(@MemberNoFrom, 1, PATINDEX('%[0-9]%', @MemberNoFrom)-1, '') AS BIGINT)
SELECT @MemberNoTo=CAST(STUFF(@MemberNoTo, 1, PATINDEX('%[0-9]%', @MemberNoTo)-1, '') AS BIGINT)

	--SELECT ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS [S No.],   
	SELECT ROW_NUMBER() over (order by CAST(STUFF(a.PolicyNo, 1, patindex('%[0-9]%', a.PolicyNo)-1, '') AS BIGINT)) AS [S No.] ,
	a.PolicyNo As [Member No],a.EmployeeId,a.Name,
	a.NepName AS[Nepali Name],CONVERT(VARCHAR(10),a.DOC,103) AS [DOC],
	CONVERT(VARCHAR(10),a.DOB,103) AS [DOB],CONVERT(VARCHAR(10),a.MaturityDate,103) AS [Maturity Date],
	a.Age,CAST(a.Term AS VARCHAR(10)) Term ,a.SumAssured AS SA,BasicPremium=
	CASE WHEN ISNULL(a.BasicPremium,0)>1 THEN a.BasicPremium ELSE a.Premium END ,ISNULL(a.ExtraPremium,0) AS ADB,a.Premium As Premium,
	c.PaidAmount,c.Instalment,CONVERT(VARCHAR(10),c.FUP,103) AS [Next Due Date],a.NomineeName,
	CAST(STUFF(a.PolicyNo, 1, PATINDEX('%[0-9]%', a.PolicyNo)-1, '') AS BIGINT) AS SortIndex
	--ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS SortIndex
	INTO #TempGroupApprove  FROM tblGroupEndowment a WITH(NOLOCK)
	INNER JOIN tblGroupInformation b 
	ON a.GroupId=b.GroupId 
	LEFT JOIN dbo.tblGroupEndowmentDetails c ON a.PolicyNo=c.PolicyNo
	WHERE a.GroupId=ISNULL(@GroupId,a.GroupId)
	
	
	AND a.DOC BETWEEN ISNULL(@DOCDateFrom,a.DOC) AND ISNULL(@DOCDateTo,A.DOC)
	AND a.Age=ISNULL(@Age,a.Age) 
	AND c.Instalment=ISNULL(@Instalment,c.Instalment)
	AND a.PolicyStatus=ISNULL(@PolicyStatus,'A')	
	AND a.ApprovedDate  IS NOT NULL
	ORDER BY a.rowid

	

	Select [S No.],
           [Member No],
           EmployeeId,
           Name,
           [Nepali Name],
           DOC,
           DOB,
           [Maturity Date],
           Age,
           Term,
           SA,
           BasicPremium,
           ADB,
           Premium,
		   PaidAmount,
		   Instalment,
           [Next Due Date],
           NomineeName,
           SortIndex INTO #TempGroupApprove1 From #TempGroupApprove 
	WHERE SortIndex 
	BETWEEN ISNULL(@MemberNoFrom,SortIndex) AND ISNULL(@MemberNoTo,SortIndex) 
	UNION ALL
	SELECT MAX([SortIndex]) + 1,'Total','','','','','','','','',SUM(SA),SUM(BasicPremium),SUM(ADB),SUM(Premium),SUM(PaidAmount),'','' ,'',MAX([SortIndex]+1)
	FROM #TempGroupApprove Order By SortIndex
	


	ALTER TABLE #TempGroupApprove1 ALTER COLUMN SortIndex BIGINT


	SELECT ROW_NUMBER() OVER(ORDER BY SortIndex ASC ) AS [SNo.],* 
	INTO #TempGroupApprove2 FROM #TempGroupApprove1 
	
	ALTER TABLE #TempGroupApprove2 DROP COLUMN [S No.]


	SELECT [SNo.],[Member No],EmployeeId,Name,[Nepali Name],DOC,DOB,[Maturity Date],Age,Term,SA,BasicPremium,ADB,Premium,PaidAmount,Instalment,[Next Due Date],NomineeName
 FROM   #TempGroupApprove2 
	Order By SortIndex ASC

	select * from  #tempSearchParameterInformation
	DROP TABLE #TempGroupApprove1
DROP TABLE #TempGroupApprove
DROP TABLE #tempSearchParameterInformation
	RETURN;

END



ELSE IF @PolicyStatus IN ('U') AND @GroupId IN ('GE1001','GE1002','GE1003','GE1003','GE1004','GE1005','GE1022')
BEGIN

	SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupName As [Group Name], @FiscalYear AS [Fiscal Year],
CONVERT(VARCHAR(10),@GroupId,105) AS [Group Master Policy:],
CONVERT(VARCHAR(10),@Age,105) AS [Age:],CONVERT(VARCHAR(10),@DOCDateFrom,105) AS [DOC Date From:],
CONVERT(VARCHAR(10),@DOCDateTo,105) AS [DOC Date To:]
,@MemberNoFrom AS MemberNoFrom,@MemberNoTo AS MemberNoTo
INTO  #tempSearchParameterInformationU



SELECT @MemberNoFrom=CAST(STUFF(@MemberNoFrom, 1, PATINDEX('%[0-9]%', @MemberNoFrom)-1, '') AS BIGINT)
SELECT @MemberNoTo=CAST(STUFF(@MemberNoTo, 1, PATINDEX('%[0-9]%', @MemberNoTo)-1, '') AS BIGINT)

	--SELECT ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS [S No.],   
	SELECT ROW_NUMBER() over (order by CAST(STUFF(a.PolicyNo, 1, patindex('%[0-9]%', a.PolicyNo)-1, '') AS BIGINT)) AS [S No.] ,
	a.PolicyNo As [Member No],a.EmployeeId,a.Name,
	a.NepName AS[Nepali Name],CONVERT(VARCHAR(10),a.DOC,103) AS [DOC],
	CONVERT(VARCHAR(10),a.DOB,103) AS [DOB],CONVERT(VARCHAR(10),a.MaturityDate,103) AS [Maturity Date],
	a.Age,CAST(a.Term AS VARCHAR(10)) Term ,a.SumAssured AS SA,BasicPremium=
	CASE WHEN ISNULL(a.BasicPremium,0)>1 THEN a.BasicPremium ELSE a.Premium END ,ISNULL(a.ExtraPremium,0) AS ADB,a.Premium As Premium,
	a.LateFine,
	CAST(STUFF(a.PolicyNo, 1, PATINDEX('%[0-9]%', a.PolicyNo)-1, '') AS BIGINT) AS SortIndex,a.NomineeName
	--ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS SortIndex
	INTO #TempGroupUnapprove  FROM tblGroupEndowment a WITH(NOLOCK)
	INNER JOIN tblGroupInformation b 
	ON a.GroupId=b.GroupId 
	WHERE a.GroupId=ISNULL(@GroupId,a.GroupId) 
	
	AND a.DOC BETWEEN ISNULL(@DOCDateFrom,a.DOC) AND ISNULL(@DOCDateTo,A.DOC)
	AND a.Age=ISNULL(@Age,a.Age) 

	AND a.PolicyStatus=ISNULL(@PolicyStatus,'U')	
	
	ORDER BY a.rowid

	
	
	Select [S No.],	[Member No],EmployeeId,Name,[Nepali Name],DOC,DOB,[Maturity Date],Age,Term,SA,BasicPremium,ADB,Premium,LateFine,SortIndex,NomineeName
 INTO #TempGroupUnapprove1 From #TempGroupUnapprove 
	 
	UNION ALL
	SELECT MAX([S No.]) + 1,'Total','','','','','','','','',SUM(SA),SUM(BasicPremium),SUM(ADB),SUM(Premium),SUM(LateFine) ,MAX([S No.]+1),''
	FROM #TempGroupUnapprove Order By SortIndex ASC


	ALTER TABLE #TempGroupUnapprove1 ALTER COLUMN SortIndex BIGINT


	SELECT ROW_NUMBER() OVER(ORDER BY SortIndex ASC ) AS [SNo.],* 
	INTO #TempGroupUnapprove2 FROM #TempGroupUnapprove1 
	
	ALTER TABLE #TempGroupUnapprove2 DROP COLUMN [S No.]


	SELECT [SNo.],	[Member No],EmployeeId,Name,[Nepali Name],DOC,DOB,[Maturity Date],Age,Term,SA,BasicPremium,ADB,Premium,LateFine,NomineeName FROM   #TempGroupUnapprove2 
	Order By SortIndex ASC

	select * from  #tempSearchParameterInformationU
	DROP TABLE #TempGroupUnapprove1
DROP TABLE #TempGroupUnapprove
DROP TABLE #tempSearchParameterInformationU
	RETURN;

END


ELSE IF @PolicyStatus='T' AND @GroupId IN ('GE1001','GE1002','GE1003','GE1003','GE1004','GE1005','GE1022')
BEGIN
SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupName As [Group Name], @FiscalYear AS [Fiscal Year],
CONVERT(VARCHAR(10),@GroupId,105) AS [Group Master Policy:],
CONVERT(VARCHAR(10),@Age,105) AS [Age:],CONVERT(VARCHAR(10),@DOCDateFrom,105) AS [DOC Date From:],
CONVERT(VARCHAR(10),@DOCDateTo,105) AS [DOC Date To:]
,@MemberNoFrom AS MemberNoFrom,@MemberNoTo AS MemberNoTo
INTO  #tempSearchParameterInformation2

SELECT @MemberNoFrom=CAST(STUFF(@MemberNoFrom, 1, PATINDEX('%[0-9]%', @MemberNoFrom)-1, '') AS BIGINT)
SELECT @MemberNoTo=CAST(STUFF(@MemberNoTo, 1, PATINDEX('%[0-9]%', @MemberNoTo)-1, '') AS BIGINT)

	--SELECT ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS [S No.],   
	SELECT ROW_NUMBER() over (order by CAST(STUFF(a.PolicyNo, 1, patindex('%[0-9]%', a.PolicyNo)-1, '') AS BIGINT)) AS [S No.] ,
	a.PolicyNo As [Member No],a.EmployeeId,a.Name,
	a.NepName AS[Nepali Name],CONVERT(VARCHAR(10),a.DOC,103) AS [DOC],
	CONVERT(VARCHAR(10),a.DOB,103) AS [DOB],CONVERT(VARCHAR(10),a.MaturityDate,103) AS [Maturity Date],
	a.Age,CAST(a.Term AS VARCHAR(10)) Term ,a.SumAssured AS SA,BasicPremium=
	CASE WHEN ISNULL(a.BasicPremium,0)>1 THEN a.BasicPremium ELSE a.Premium END ,ISNULL(a.ExtraPremium,0) AS ADB,a.Premium As Premium,
	c.PaidAmount,c.Instalment,a.LateFine,CONVERT(VARCHAR(10),a.TerminationDate,103) AS [Terminate Date],a.TerminateBy,a.TerminateRemarks,
	CAST(STUFF(a.PolicyNo, 1, PATINDEX('%[0-9]%', a.PolicyNo)-1, '') AS BIGINT) AS SortIndex
	--ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS SortIndex
	INTO #TempGroupTerminate    FROM tblGroupEndowment a WITH(NOLOCK)
	INNER JOIN tblGroupInformation b 
	ON a.GroupId=b.GroupId 
	LEFT JOIN dbo.tblGroupEndowmentDetails c ON a.PolicyNo=c.PolicyNo
	WHERE a.GroupId=ISNULL(@GroupId,a.GroupId) AND a.Premium=c.Premium
	
	AND a.DOC BETWEEN ISNULL(@DOCDateFrom,a.DOC) AND ISNULL(@DOCDateTo,A.DOC)
	AND a.Age=ISNULL(@Age,a.Age) 
	AND c.Instalment=ISNULL(@Instalment,c.Instalment)
	AND a.PolicyStatus=ISNULL(@PolicyStatus,'A')	
	ORDER BY a.rowid

	

	Select * INTO #TempGroupTerminate1  From #TempGroupTerminate  
	WHERE SortIndex 
	BETWEEN ISNULL(@MemberNoFrom,SortIndex) AND ISNULL(@MemberNoTo,SortIndex) 
	UNION ALL
	SELECT MAX([SortIndex]) + 1,'Total','','','','','','','','',SUM(SA),SUM(BasicPremium),SUM(ADB),SUM(Premium),SUM(PaidAmount),'','','','','' ,MAX([SortIndex]+1)
	FROM #TempGroupTerminate  Order By SortIndex
	


	ALTER TABLE #TempGroupTerminate1 ALTER COLUMN SortIndex BIGINT


	SELECT ROW_NUMBER() OVER(ORDER BY SortIndex ASC ) AS [SNo.],* 
	INTO #TempGroupTerminate2 FROM #TempGroupTerminate1 
	
	ALTER TABLE #TempGroupTerminate2 DROP COLUMN [S No.]


	SELECT * FROM   #TempGroupTerminate2 
	Order By SortIndex ASC

	select * from  #tempSearchParameterInformation2
	DROP TABLE #TempGroupTerminate
DROP TABLE #TempGroupTerminate1
DROP TABLE #TempGroupTerminate2

	RETURN;

	
END
--------------------------------------------------------------------------------------------------------------------
ELSE IF @PolicyStatus='C' AND @GroupId IN ('GE1001','GE1002','GE1003','GE1003','GE1004','GE1005','GE1022')
BEGIN
SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupName As [Group Name], @FiscalYear AS [Fiscal Year],
CONVERT(VARCHAR(10),@GroupId,105) AS [Group Master Policy:],
CONVERT(VARCHAR(10),@Age,105) AS [Age:],CONVERT(VARCHAR(10),@DOCDateFrom,105) AS [DOC Date From:],
CONVERT(VARCHAR(10),@DOCDateTo,105) AS [DOC Date To:]
,@MemberNoFrom AS MemberNoFrom,@MemberNoTo AS MemberNoTo
INTO  #tempSearchParameterInformation3



SELECT @MemberNoFrom=CAST(STUFF(@MemberNoFrom, 1, PATINDEX('%[0-9]%', @MemberNoFrom)-1, '') AS BIGINT)
SELECT @MemberNoTo=CAST(STUFF(@MemberNoTo, 1, PATINDEX('%[0-9]%', @MemberNoTo)-1, '') AS BIGINT)

	--SELECT ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS [S No.],   
	SELECT ROW_NUMBER() over (order by CAST(STUFF(a.PolicyNo, 1, patindex('%[0-9]%', a.PolicyNo)-1, '') AS BIGINT)) AS [S No.] ,
	a.PolicyNo As [Member No],a.EmployeeId,a.Name,
	a.NepName AS[Nepali Name],CONVERT(VARCHAR(10),a.DOC,103) AS [DOC],
	CONVERT(VARCHAR(10),a.DOB,103) AS [DOB],CONVERT(VARCHAR(10),a.MaturityDate,103) AS [Maturity Date],
	a.Age,CAST(a.Term AS VARCHAR(10)) Term ,a.SumAssured AS SA,BasicPremium=
	CASE WHEN ISNULL(a.BasicPremium,0)>1 THEN a.BasicPremium ELSE a.Premium END ,ISNULL(a.ExtraPremium,0) AS ADB,a.Premium As Premium,
	c.PaidAmount,c.Instalment,a.LateFine,CONVERT(VARCHAR(10),a.CancelDate,103) AS [Cancel Date],a.CancelBy,a.CancelRemarks,
	CAST(STUFF(a.PolicyNo, 1, PATINDEX('%[0-9]%', a.PolicyNo)-1, '') AS BIGINT) AS SortIndex
	--ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS SortIndex
	INTO #TempGroupCancel      FROM tblGroupEndowment a WITH(NOLOCK)
	INNER JOIN tblGroupInformation b 
	ON a.GroupId=b.GroupId 
	LEFT JOIN dbo.tblGroupEndowmentDetails c ON a.PolicyNo=c.PolicyNo
	WHERE a.GroupId=ISNULL(@GroupId,a.GroupId) AND a.Premium=c.Premium
	
	AND a.DOC BETWEEN ISNULL(@DOCDateFrom,a.DOC) AND ISNULL(@DOCDateTo,A.DOC)
	AND a.Age=ISNULL(@Age,a.Age) 
	AND c.Instalment=ISNULL(@Instalment,c.Instalment)
	AND a.PolicyStatus=ISNULL(@PolicyStatus,'A')	
	ORDER BY a.rowid

	

	Select * INTO #TempGroupCancel1    From #TempGroupCancel    
	WHERE SortIndex 
	BETWEEN ISNULL(@MemberNoFrom,SortIndex) AND ISNULL(@MemberNoTo,SortIndex) 
	UNION ALL
	SELECT MAX([SortIndex]) + 1,'Total','','','','','','','','',SUM(SA),SUM(BasicPremium),SUM(ADB),SUM(Premium),SUM(PaidAmount),'','','','','' ,MAX([SortIndex]+1)
	FROM #TempGroupCancel    Order By SortIndex
	


	ALTER TABLE #TempGroupCancel1   ALTER COLUMN SortIndex BIGINT


	SELECT ROW_NUMBER() OVER(ORDER BY SortIndex ASC ) AS [SNo.],* 
	INTO #TempGroupCancel2   FROM #TempGroupCancel1   
	
	ALTER TABLE #TempGroupCancel2 DROP COLUMN [S No.]


	SELECT * FROM   #TempGroupCancel2 
	Order By SortIndex ASC

	select * from  #tempSearchParameterInformation3
	DROP TABLE #TempGroupCancel
DROP TABLE #TempGroupCancel1
DROP TABLE #TempGroupCancel2
DROP TABLE #tempSearchParameterInformation3
	RETURN;

	
END

ELSE IF @PolicyStatus='L' AND @GroupId IN ('GE1001','GE1002','GE1003','GE1003','GE1004','GE1005','GE1022')
BEGIN

	SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupName As [Group Name], @FiscalYear AS [Fiscal Year],
CONVERT(VARCHAR(10),@GroupId,105) AS [Group Master Policy:],
CONVERT(VARCHAR(10),@Age,105) AS [Age:],CONVERT(VARCHAR(10),@DOCDateFrom,105) AS [DOC Date From:],
CONVERT(VARCHAR(10),@DOCDateTo,105) AS [DOC Date To:]
,@MemberNoFrom AS MemberNoFrom,@MemberNoTo AS MemberNoTo
INTO  #tempSearchParameterInformation4



SELECT @MemberNoFrom=CAST(STUFF(@MemberNoFrom, 1, PATINDEX('%[0-9]%', @MemberNoFrom)-1, '') AS BIGINT)
SELECT @MemberNoTo=CAST(STUFF(@MemberNoTo, 1, PATINDEX('%[0-9]%', @MemberNoTo)-1, '') AS BIGINT)

	--SELECT ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS [S No.],   
	SELECT ROW_NUMBER() over (order by CAST(STUFF(a.PolicyNo, 1, patindex('%[0-9]%', a.PolicyNo)-1, '') AS BIGINT)) AS [S No.] ,
	a.PolicyNo As [Member No],a.EmployeeId,a.Name,
	a.NepName AS[Nepali Name],CONVERT(VARCHAR(10),a.DOC,103) AS [DOC],
	CONVERT(VARCHAR(10),a.DOB,103) AS [DOB],CONVERT(VARCHAR(10),a.MaturityDate,103) AS [Maturity Date],
	a.Age,CAST(a.Term AS VARCHAR(10)) Term ,a.SumAssured AS SA,BasicPremium=
	CASE WHEN ISNULL(a.BasicPremium,0)>1 THEN a.BasicPremium ELSE a.Premium END ,ISNULL(a.ExtraPremium,0) AS ADB,a.Premium As Premium,
	c.PaidAmount,c.Instalment,a.LateFine,CONVERT(VARCHAR(10),a.LapseDate,103) AS [Lapse Date],a.LapseBy,a.LapseRemarks,
	CAST(STUFF(a.PolicyNo, 1, PATINDEX('%[0-9]%', a.PolicyNo)-1, '') AS BIGINT) AS SortIndex
	--ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS SortIndex
	INTO #TempGroupLapse   FROM tblGroupEndowment a WITH(NOLOCK)
	INNER JOIN tblGroupInformation b 
	ON a.GroupId=b.GroupId 
	LEFT JOIN dbo.tblGroupEndowmentDetails c ON a.PolicyNo=c.PolicyNo
	WHERE a.GroupId=ISNULL(@GroupId,a.GroupId) 
	
	
	AND a.DOC BETWEEN ISNULL(@DOCDateFrom,a.DOC) AND ISNULL(@DOCDateTo,A.DOC)
	AND a.Age=ISNULL(@Age,a.Age) 
	AND c.Instalment=ISNULL(@Instalment,c.Instalment)
	AND a.PolicyStatus=ISNULL(@PolicyStatus,'A')	
	ORDER BY a.rowid

	

	Select * INTO #TempGroupLapse1      From #TempGroupLapse      
	WHERE SortIndex 
	BETWEEN ISNULL(@MemberNoFrom,SortIndex) AND ISNULL(@MemberNoTo,SortIndex) 
	UNION ALL
	SELECT MAX([SortIndex]) + 1,'Total','','','','','','','','',SUM(SA),SUM(BasicPremium),SUM(ADB),SUM(Premium),SUM(PaidAmount),'','' ,'','','',MAX([SortIndex]+1)
	FROM #TempGroupLapse      Order By SortIndex
	


	ALTER TABLE #TempGroupLapse1   ALTER COLUMN SortIndex BIGINT


	SELECT ROW_NUMBER() OVER(ORDER BY SortIndex ASC ) AS [SNo.],* 
	INTO #TempGroupLapse2   FROM #TempGroupLapse1   
	
	ALTER TABLE #TempGroupLapse2 DROP COLUMN [S No.]


	SELECT * FROM   #TempGroupLapse2 
	Order By SortIndex ASC

	select * from  #tempSearchParameterInformation4
	DROP TABLE #TempGroupLapse
DROP TABLE #TempGroupLapse1
DROP TABLE #TempGroupLapse2
DROP TABLE #tempSearchParameterInformation4
	RETURN;


END


IF @PolicyStatus IN ('A') AND @GroupId NOT IN ('GE1001','GE1002','GE1003','GE1003','GE1004','GE1005','GE1022')
BEGIN

	SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupName As [Group Name], @FiscalYear AS [Fiscal Year],
CONVERT(VARCHAR(10),@GroupId,105) AS [Group Master Policy:],
CONVERT(VARCHAR(10),@Age,105) AS [Age:],CONVERT(VARCHAR(10),@DOCDateFrom,105) AS [DOC Date From:],
CONVERT(VARCHAR(10),@DOCDateTo,105) AS [DOC Date To:]
,@MemberNoFrom AS MemberNoFrom,@MemberNoTo AS MemberNoTo
INTO  #GrouptempSearchParameterInformation



SELECT @MemberNoFrom=CAST(STUFF(@MemberNoFrom, 1, PATINDEX('%[-]%', @MemberNoFrom), '') AS BIGINT)
SELECT @MemberNoTo=CAST(STUFF(@MemberNoTo, 1, PATINDEX('%[-]%', @MemberNoTo), '') AS BIGINT)

	--SELECT ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS [S No.],   
	SELECT ROW_NUMBER() over (order by CAST(STUFF(a.PolicyNo, 1, patindex('%[-]%', a.PolicyNo), '') AS BIGINT)) AS [S No.] ,
	a.PolicyNo As [Member No],a.EmployeeId,a.Name,
	a.NepName AS[Nepali Name],CONVERT(VARCHAR(10),a.DOC,103) AS [DOC],
	CONVERT(VARCHAR(10),a.DOB,103) AS [DOB],CONVERT(VARCHAR(10),a.MaturityDate,103) AS [Maturity Date],
	a.Age,CAST(a.Term AS VARCHAR(10)) Term ,a.SumAssured AS SA,BasicPremium=
	CASE WHEN ISNULL(a.BasicPremium,0)>1 THEN a.BasicPremium ELSE a.Premium END ,ISNULL(a.ExtraPremium,0) AS ADB,ModeExtra=a.EXT_PREMIUM,a.Premium As Premium,
	c.PaidAmount,c.Instalment,CONVERT(VARCHAR(10),a.FUP,103) AS [Next Due Date],a.PolicyStatus,
	CAST(STUFF(a.PolicyNo, 1, PATINDEX('%[-]%', a.PolicyNo), '') AS BIGINT) AS SortIndex
	--ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS SortIndex
	INTO #GroupTempGroupApprove  FROM tblGroupEndowment a WITH(NOLOCK)
	INNER JOIN tblGroupInformation b 
	ON a.GroupId=b.GroupId 
	LEFT JOIN dbo.tblGroupEndowmentDetails c ON a.RegisterNo=c.RegisterNo
	WHERE a.GroupId=ISNULL(@GroupId,a.GroupId)

	
	AND a.DOC BETWEEN ISNULL(@DOCDateFrom,a.DOC) AND ISNULL(@DOCDateTo,a.DOC)
	AND a.Age=ISNULL(@Age,a.Age) 
	AND c.Instalment=ISNULL(@Instalment,c.Instalment)
	AND a.PolicyStatus=ISNULL(@PolicyStatus,'A')	
	AND a.ApprovedDate  IS NOT NULL
	ORDER BY a.rowid

	

	Select * INTO #GroupTempGroupApprove1 From #GroupTempGroupApprove 
	WHERE SortIndex 
	BETWEEN ISNULL(@MemberNoFrom,SortIndex) AND ISNULL(@MemberNoTo,SortIndex) 
	UNION ALL
	SELECT MAX([SortIndex]) + 1,'Total','','','','','','','','',SUM(SA),SUM(BasicPremium),SUM(ADB),SUM(ModeExtra),SUM(Premium),SUM(PaidAmount),'','','' ,MAX([SortIndex]+1)
	FROM #GroupTempGroupApprove Order By SortIndex
	


	ALTER TABLE #GroupTempGroupApprove1 ALTER COLUMN SortIndex BIGINT


	SELECT ROW_NUMBER() OVER(ORDER BY SortIndex ASC ) AS [SNo.],* 
	INTO #GroupTempGroupApprove2 FROM #GroupTempGroupApprove1 
	
	ALTER TABLE #GroupTempGroupApprove2 DROP COLUMN [S No.]


	SELECT [SNo.],[Member No],EmployeeId,Name,[Nepali Name],DOC,DOB,[Maturity Date],Age,Term,SA,BasicPremium,ADB,ModeExtra,Premium,Instalment,[Next Due Date] FROM   #GroupTempGroupApprove2 
	Order By SortIndex ASC

	select * from  #GrouptempSearchParameterInformation
	DROP TABLE #GroupTempGroupApprove1
DROP TABLE #GroupTempGroupApprove
DROP TABLE #GrouptempSearchParameterInformation
	RETURN;

END



ELSE IF @PolicyStatus IN ('U') AND @GroupId NOT IN ('GE1001','GE1002','GE1003','GE1003','GE1004','GE1005','GE1022')
BEGIN

	SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupName As [Group Name], @FiscalYear AS [Fiscal Year],
CONVERT(VARCHAR(10),@GroupId,105) AS [Group Master Policy:],
CONVERT(VARCHAR(10),@Age,105) AS [Age:],CONVERT(VARCHAR(10),@DOCDateFrom,105) AS [DOC Date From:],
CONVERT(VARCHAR(10),@DOCDateTo,105) AS [DOC Date To:]
,@MemberNoFrom AS MemberNoFrom,@MemberNoTo AS MemberNoTo
INTO  #GrouptempSearchParameterInformationU



SELECT @MemberNoFrom=CAST(STUFF(@MemberNoFrom, 1, PATINDEX('%[-]%', @MemberNoFrom), '') AS BIGINT)
SELECT @MemberNoTo=CAST(STUFF(@MemberNoTo, 1, PATINDEX('%[-]%', @MemberNoTo), '') AS BIGINT)

	--SELECT ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS [S No.],   
	SELECT ROW_NUMBER() over (order by CAST(STUFF(a.PolicyNo, 1, patindex('%[-]%', a.PolicyNo), '') AS BIGINT)) AS [S No.] ,
	a.PolicyNo As [Member No],a.EmployeeId,a.Name,
	a.NepName AS[Nepali Name],a.DOC,
	CONVERT(VARCHAR(10),a.DOB,103) AS [DOB],CONVERT(VARCHAR(10),a.MaturityDate,103) AS [Maturity Date],
	a.Age,CAST(a.Term AS VARCHAR(10)) Term ,a.SumAssured AS SA,BasicPremium=
	CASE WHEN ISNULL(a.BasicPremium,0)>1 THEN a.BasicPremium ELSE a.Premium END ,ISNULL(a.ADBPremium,0) AS ADB,a.Premium AS Premium,
	a.LateFine,Total=a.Premium+a.LateFine,a.RegisterNo,
	CAST(STUFF(a.PolicyNo, 1, PATINDEX('%[-]%', a.PolicyNo), '') AS BIGINT) AS SortIndex
	--ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS SortIndex
	INTO #GroupTempGroupUnapprove  FROM tblGroupEndowment a WITH(NOLOCK)
	INNER JOIN tblGroupInformation b 
	ON a.GroupId=b.GroupId 
	WHERE a.GroupId=ISNULL(@GroupId,a.GroupId) 
	
	AND a.DOC BETWEEN ISNULL(@DOCDateFrom,a.DOC) AND ISNULL(@DOCDateTo,A.DOC)
	AND a.Age=ISNULL(@Age,a.Age) 

	AND a.PolicyStatus=ISNULL(@PolicyStatus,'U')	
	
	ORDER BY a.rowid


	ALTER TABLE #GroupTempGroupUnapprove ALTER COLUMN LateFine MONEY
	
	ALTER TABLE #GroupTempGroupUnapprove ADD LateFineRate MONEY,DayCount MONEY

UPDATE #GroupTempGroupUnapprove SET DayCount =DATEDIFF(DAY,DOC,GETDATE())
UPDATE #GroupTempGroupUnapprove SET LateFine =0 WHERE DayCount <=30
UPDATE #GroupTempGroupUnapprove SET LateFine =5 WHERE DayCount  BETWEEN 30 AND 45

UPDATE #GroupTempGroupUnapprove SET LateFineRate = (SELECT ISNULL(Rate,0) FROM latefeerate WHERE DayCount BETWEEN StartDays AND EndDays) WHERE DayCount >45
UPDATE #GroupTempGroupUnapprove SET LateFine= ROUND((premium*(DayCount/365.00)*LateFineRate)/100.00,0) WHERE DayCount >45
UPDATE #GroupTempGroupUnapprove SET LateFine=0 WHERE LateFine IS NULL

--UPDATE #GroupTempGroupUnapprove SET Total=Premium+isnull(LateFine,0)

UPDATE #GroupTempGroupUnapprove SET Total=Premium+ISNULL(LateFine,0)

IF @GroupId='018'
BEGIN
UPDATE #GroupTempGroupUnapprove SET Total=Premium+ISNULL(0,0),LateFine=0
END




	SELECT * INTO #GroupTempGroupUnapprove1 FROM #GroupTempGroupUnapprove 
	 
	UNION ALL
	SELECT MAX([SortIndex]) + 1,'Total','','','','','','','','',SUM(SA),SUM(BasicPremium),SUM(ADB),SUM(Premium),SUM(LateFine),SUM(Total),'',MAX([SortIndex]+1),SUM(LateFine),SUM(DayCount)
	FROM #GroupTempGroupUnapprove ORDER BY SortIndex
	
	
	--SELECT * FROM  #GroupTempGroupApprove AS gtgaADBSA
	--RETURN
	

	ALTER TABLE #GroupTempGroupUnapprove1 ALTER COLUMN SortIndex BIGINT


	SELECT ROW_NUMBER() OVER(ORDER BY SortIndex ASC ) AS [SNo.],* 
	INTO #GroupTempGroupUnapprove2 FROM #GroupTempGroupUnapprove1 
	
	ALTER TABLE #GroupTempGroupUnapprove2 DROP COLUMN [S No.]

	--UPDATE #GroupTempGroupUnapprove2 SET Total=0,LateFine=0 WHERE GroupID='018'

	SELECT [SNo.],[Member No],EmployeeId,Name,[Nepali Name],DOC=CONVERT(VARCHAR(10),DOC,103),DOB,[Maturity Date],Age,Term,SA,BasicPremium,ADB,Premium,LateFine,Total,RegisterNo	 FROM   #GroupTempGroupUnapprove2 
	ORDER BY SortIndex ASC
	--		IF @GroupId='075'
	--BEGIN
	--SELECT 'a'
	--END
	SELECT * FROM  #GrouptempSearchParameterInformationU
	DROP TABLE #GroupTempGroupUnapprove1
DROP TABLE #GroupTempGroupUnapprove
DROP TABLE #GrouptempSearchParameterInformationU
	RETURN;

END

----------------------------------------------------------------------------------------------------------------------------------
ELSE IF @PolicyStatus='T' AND @GroupId NOT IN ('GE1001','GE1002','GE1003','GE1003','GE1004','GE1005','GE1022')
BEGIN
SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupName As [Group Name], @FiscalYear AS [Fiscal Year],
CONVERT(VARCHAR(10),@GroupId,105) AS [Group Master Policy:],
CONVERT(VARCHAR(10),@Age,105) AS [Age:],CONVERT(VARCHAR(10),@DOCDateFrom,105) AS [DOC Date From:],
CONVERT(VARCHAR(10),@DOCDateTo,105) AS [DOC Date To:]
,@MemberNoFrom AS MemberNoFrom,@MemberNoTo AS MemberNoTo
INTO  #GrouptempSearchParameterInformation2



SELECT @MemberNoFrom=CAST(STUFF(@MemberNoFrom, 1, PATINDEX('%[0-]%', @MemberNoFrom), '') AS BIGINT)
SELECT @MemberNoTo=CAST(STUFF(@MemberNoTo, 1, PATINDEX('%[-]%', @MemberNoTo), '') AS BIGINT)

	--SELECT ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS [S No.],   
	SELECT ROW_NUMBER() over (order by CAST(STUFF(a.PolicyNo, 1, patindex('%[-]%', a.PolicyNo), '') AS BIGINT)) AS [S No.] ,
	a.PolicyNo As [Member No],a.EmployeeId,a.Name,
	a.NepName AS[Nepali Name],CONVERT(VARCHAR(10),a.DOC,103) AS [DOC],
	CONVERT(VARCHAR(10),a.DOB,103) AS [DOB],CONVERT(VARCHAR(10),a.MaturityDate,103) AS [Maturity Date],
	a.Age,CAST(a.Term AS VARCHAR(10)) Term ,a.SumAssured AS SA,BasicPremium=
	CASE WHEN ISNULL(a.BasicPremium,0)>1 THEN a.BasicPremium ELSE a.Premium END ,ISNULL(a.ExtraPremium,0) AS ADB,a.Premium As Premium,
	c.PaidAmount,c.Instalment,a.LateFine,CONVERT(VARCHAR(10),a.TerminationDate,103) AS [Terminate Date],a.TerminateBy,a.TerminateRemarks,
	CAST(STUFF(a.PolicyNo, 1, PATINDEX('%[-]%', a.PolicyNo), '') AS BIGINT) AS SortIndex
	--ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS SortIndex
	INTO #GroupTempGroupTerminate    FROM tblGroupEndowment a WITH(NOLOCK)
	INNER JOIN tblGroupInformation b 
	ON a.GroupId=b.GroupId 
	LEFT JOIN dbo.tblGroupEndowmentDetails c ON a.RegisterNo=c.RegisterNo
	WHERE a.GroupId=ISNULL(@GroupId,a.GroupId) AND a.Premium=c.Premium
	
	AND a.DOC BETWEEN ISNULL(@DOCDateFrom,a.DOC) AND ISNULL(@DOCDateTo,A.DOC)
	AND a.Age=ISNULL(@Age,a.Age) 
	AND c.Instalment=ISNULL(@Instalment,c.Instalment)
	AND a.PolicyStatus IN('S','D','M','I')	
	ORDER BY a.rowid

	

	Select * INTO #GroupTempGroupTerminate1  From #GroupTempGroupTerminate  
	WHERE SortIndex 
	BETWEEN ISNULL(@MemberNoFrom,SortIndex) AND ISNULL(@MemberNoTo,SortIndex) 
	UNION ALL
	SELECT MAX([SortIndex]) + 1,'Total','','','','','','','','',SUM(SA),SUM(BasicPremium),SUM(ADB),SUM(Premium),SUM(PaidAmount),'','','','','' ,MAX([SortIndex]+1)
	FROM #GroupTempGroupTerminate  Order By SortIndex
	


	ALTER TABLE #GroupTempGroupTerminate1 ALTER COLUMN SortIndex BIGINT


	SELECT ROW_NUMBER() OVER(ORDER BY SortIndex ASC ) AS [SNo.],* 
	INTO #GroupTempGroupTerminate2 FROM #GroupTempGroupTerminate1 
	
	ALTER TABLE #GroupTempGroupTerminate2 DROP COLUMN [S No.]


	SELECT * FROM   #GroupTempGroupTerminate2 
	Order By SortIndex ASC

	select * from  #GrouptempSearchParameterInformation2
	DROP TABLE #GroupTempGroupTerminate
DROP TABLE #GroupTempGroupTerminate1
DROP TABLE #GroupTempGroupTerminate2

	RETURN;

	
END

ELSE IF @PolicyStatus='C' AND @GroupId NOT IN ('GE1001','GE1002','GE1003','GE1003','GE1004','GE1005','GE1022')
BEGIN
SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupName As [Group Name], @FiscalYear AS [Fiscal Year],
CONVERT(VARCHAR(10),@GroupId,105) AS [Group Master Policy:],
CONVERT(VARCHAR(10),@Age,105) AS [Age:],CONVERT(VARCHAR(10),@DOCDateFrom,105) AS [DOC Date From:],
CONVERT(VARCHAR(10),@DOCDateTo,105) AS [DOC Date To:]
,@MemberNoFrom AS MemberNoFrom,@MemberNoTo AS MemberNoTo
INTO  #GrouptempSearchParameterInformation3



SELECT @MemberNoFrom=CAST(STUFF(@MemberNoFrom, 1, PATINDEX('%[-]%', @MemberNoFrom), '') AS BIGINT)
SELECT @MemberNoTo=CAST(STUFF(@MemberNoTo, 1, PATINDEX('%[-]%', @MemberNoTo), '') AS BIGINT)

	--SELECT ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS [S No.],   
	SELECT ROW_NUMBER() over (order by CAST(STUFF(a.PolicyNo, 1, patindex('%[-]%', a.PolicyNo), '') AS BIGINT)) AS [S No.] ,
	a.PolicyNo As [Member No],a.EmployeeId,a.Name,
	a.NepName AS[Nepali Name],CONVERT(VARCHAR(10),a.DOC,103) AS [DOC],
	CONVERT(VARCHAR(10),a.DOB,103) AS [DOB],CONVERT(VARCHAR(10),a.MaturityDate,103) AS [Maturity Date],
	a.Age,CAST(a.Term AS VARCHAR(10)) Term ,a.SumAssured AS SA,BasicPremium=
	CASE WHEN ISNULL(a.BasicPremium,0)>1 THEN a.BasicPremium ELSE a.Premium END ,ISNULL(a.ExtraPremium,0) AS ADB,a.Premium As Premium,
	c.PaidAmount,c.Instalment,a.LateFine,CONVERT(VARCHAR(10),a.CancelDate,103) AS [Cancel Date],a.CancelBy,a.CancelRemarks,
	CAST(STUFF(a.PolicyNo, 1, PATINDEX('%[-]%', a.PolicyNo), '') AS BIGINT) AS SortIndex
	--ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS SortIndex
	INTO #GroupTempGroupCancel      FROM tblGroupEndowment a WITH(NOLOCK)
	INNER JOIN tblGroupInformation b 
	ON a.GroupId=b.GroupId 
	LEFT JOIN dbo.tblGroupEndowmentDetails c ON a.PolicyNo=c.PolicyNo
	WHERE a.GroupId=ISNULL(@GroupId,a.GroupId) AND a.Premium=c.Premium
	
	AND a.DOC BETWEEN ISNULL(@DOCDateFrom,a.DOC) AND ISNULL(@DOCDateTo,A.DOC)
	AND a.Age=ISNULL(@Age,a.Age) 
	AND c.Instalment=ISNULL(@Instalment,c.Instalment)
	AND a.PolicyStatus=ISNULL(@PolicyStatus,'A')	
	ORDER BY a.rowid

	

	Select * INTO #GroupTempGroupCancel1    From #GroupTempGroupCancel    
	WHERE SortIndex 
	BETWEEN ISNULL(@MemberNoFrom,SortIndex) AND ISNULL(@MemberNoTo,SortIndex) 
	UNION ALL
	SELECT MAX([SortIndex]) + 1,'Total','','','','','','','','',SUM(SA),SUM(BasicPremium),SUM(ADB),SUM(Premium),SUM(PaidAmount),'','','','','' ,MAX([SortIndex]+1)
	FROM #GroupTempGroupCancel    Order By SortIndex
	


	ALTER TABLE #GroupTempGroupCancel1   ALTER COLUMN SortIndex BIGINT


	SELECT ROW_NUMBER() OVER(ORDER BY SortIndex ASC ) AS [SNo.],* 
	INTO #GroupTempGroupCancel2   FROM #GroupTempGroupCancel1   
	
	ALTER TABLE #GroupTempGroupCancel2 DROP COLUMN [S No.]


	SELECT * FROM   #GroupTempGroupCancel2 
	Order By SortIndex ASC

	select * from  #GrouptempSearchParameterInformation3
	DROP TABLE #GroupTempGroupCancel
DROP TABLE #GroupTempGroupCancel1
DROP TABLE #GroupTempGroupCancel2
DROP TABLE #GrouptempSearchParameterInformation3
	RETURN;

	
END

ELSE IF @PolicyStatus='L' AND @GroupId NOT IN ('GE1001','GE1002','GE1003','GE1003','GE1004','GE1005','GE1022')
BEGIN

	SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupName As [Group Name], @FiscalYear AS [Fiscal Year],
CONVERT(VARCHAR(10),@GroupId,105) AS [Group Master Policy:],
CONVERT(VARCHAR(10),@Age,105) AS [Age:],CONVERT(VARCHAR(10),@DOCDateFrom,105) AS [DOC Date From:],
CONVERT(VARCHAR(10),@DOCDateTo,105) AS [DOC Date To:]
,@MemberNoFrom AS MemberNoFrom,@MemberNoTo AS MemberNoTo
INTO  #GrouptempSearchParameterInformation4



SELECT @MemberNoFrom=CAST(STUFF(@MemberNoFrom, 1, PATINDEX('%[-]%', @MemberNoFrom), '') AS BIGINT)
SELECT @MemberNoTo=CAST(STUFF(@MemberNoTo, 1, PATINDEX('%[-]%', @MemberNoTo), '') AS BIGINT)

	--SELECT ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS [S No.],   
	SELECT ROW_NUMBER() over (order by CAST(STUFF(a.PolicyNo, 1, patindex('%[-]%', a.PolicyNo), '') AS BIGINT)) AS [S No.] ,
	a.PolicyNo As [Member No],a.EmployeeId,a.Name,
	a.NepName AS[Nepali Name],CONVERT(VARCHAR(10),a.DOC,103) AS [DOC],
	CONVERT(VARCHAR(10),a.DOB,103) AS [DOB],CONVERT(VARCHAR(10),a.MaturityDate,103) AS [Maturity Date],
	a.Age,CAST(a.Term AS VARCHAR(10)) Term ,a.SumAssured AS SA,BasicPremium=
	CASE WHEN ISNULL(a.BasicPremium,0)>1 THEN a.BasicPremium ELSE a.Premium END ,ISNULL(a.ExtraPremium,0) AS ADB,a.Premium As Premium,
	c.PaidAmount,c.Instalment,a.LateFine,CONVERT(VARCHAR(10),a.LapseDate,103) AS [Lapse Date],a.LapseBy,a.LapseRemarks,
	CAST(STUFF(a.PolicyNo, 1, PATINDEX('%[-]%', a.PolicyNo)-1, '') AS BIGINT) AS SortIndex
	--ROW_NUMBER() OVER(ORDER BY a.rowid asc) AS SortIndex
	INTO #GroupTempGroupLapse   FROM tblGroupEndowment a WITH(NOLOCK)
	INNER JOIN tblGroupInformation b 
	ON a.GroupId=b.GroupId 
	LEFT JOIN dbo.tblGroupEndowmentDetails c ON a.PolicyNo=c.PolicyNo
	WHERE a.GroupId=ISNULL(@GroupId,a.GroupId) AND a.Premium=c.Premium
	
	AND a.DOC BETWEEN ISNULL(@DOCDateFrom,a.DOC) AND ISNULL(@DOCDateTo,A.DOC)
	AND a.Age=ISNULL(@Age,a.Age) 
	AND c.Instalment=ISNULL(@Instalment,c.Instalment)
	AND a.PolicyStatus=ISNULL(@PolicyStatus,'A')	
	ORDER BY a.rowid

	

	Select * INTO #GroupTempGroupLapse1      From #GroupTempGroupLapse      
	WHERE SortIndex 
	BETWEEN ISNULL(@MemberNoFrom,SortIndex) AND ISNULL(@MemberNoTo,SortIndex) 
	UNION ALL
	SELECT MAX([SortIndex]) + 1,'Total','','','','','','','','',SUM(SA),SUM(BasicPremium),SUM(ADB),SUM(Premium),SUM(PaidAmount),'','' ,'','','',MAX([SortIndex]+1)
	FROM #GroupTempGroupLapse      Order By SortIndex
	


	ALTER TABLE #GroupTempGroupLapse1   ALTER COLUMN SortIndex BIGINT


	SELECT ROW_NUMBER() OVER(ORDER BY SortIndex ASC ) AS [SNo.],* 
	INTO #GroupTempGroupLapse2   FROM #GroupTempGroupLapse1   
	
	ALTER TABLE #GroupTempGroupLapse2 DROP COLUMN [S No.]


	SELECT * FROM   #GroupTempGroupLapse2 
	Order By SortIndex ASC

	select * from  #GrouptempSearchParameterInformation4
	DROP TABLE #GroupTempGroupLapse
DROP TABLE #GroupTempGroupLapse1
DROP TABLE #GroupTempGroupLapse2
DROP TABLE #GrouptempSearchParameterInformation4
	RETURN;


END



END





ELSE IF @Flag='IndividualTransferGrid'
BEGIN
SELECT  EmployeeId,Name,NepName,PolicyNo,PreviousPolicy,TransferDate INTO #PP FROM tblgroupendowment where TransferDate IS NOT NULL order by TransferDate desc

SET @FirstRec = @DisplayStart;
	SET @LastRec = @DisplayStart + @DisplayLength;
	;WITH CTE_REPORT as
		(
			Select ROW_NUMBER() over 
			(
				ORDER BY      
				TransferDate desc 
			)
			As RowNum,
			COUNT(*) over()  AS FilterCount,
			* FROM
			#PP WHERE  (@Search IS NULL 
				
				OR PolicyNo like '%' + @Search + '%'
				OR PreviousPolicy like '%' + @Search + '%'
				OR Name like '%' + @Search + '%'
				OR EmployeeId like '%' + @Search + '%'

				
			)
		)
		Select * FROM CTE_REPORT
		Where RowNum > @FirstRec and RowNum <= @LastRec	



DROP TABLE #PP
END

ELSE IF @Flag='GetDuplicatePolicyGridDetails'
BEGIN
SELECT PolicyNo ,NepName,TotalPolicy=count(PolicyNo) INTO #tt  
FROM tblgroupendowment WHERE PolicyStatus='A' 
  GROUP BY PolicyNo ,Nepname 

  

SET @FirstRec = @DisplayStart;
	SET @LastRec = @DisplayStart + @DisplayLength;
	;WITH CTE_REPORT as
		(
			Select ROW_NUMBER() over 
			(
				ORDER BY      
				PolicyNo 
			)
			As RowNum,
			COUNT(*) over()  AS FilterCount,
			* FROM
			#tt WHERE TotalPolicy>1 AND (@Search IS NULL 
				
				OR PolicyNo like '%' + @Search + '%'
				OR NepName like '%' + @Search + '%'
			)
		)
		Select * FROM CTE_REPORT
		Where RowNum > @FirstRec and RowNum <= @LastRec	

DROP TABLE #tt
END
ELSE IF @Flag='IndividualReport'
BEGIN
SELECT a.RowId,	a.PolicyNo,	a.RegisterNo,	a.Branch,	a.PaidDate,PaidAmount=a.Premium*a.Instalment,BasicPremium=ISNULL(b.BasicPremium,0),ISNULL(b.ExtraPremium,0) AS ADBPremium,a.Premium,	a.SumAssured,	a.BatchNo,	
a.GroupId,	a.FUP,	a.Instalment,	a.PostedBy,	a.Remarks,	a.Intrest,	a.LateFine,	a.PolicyStatus,	a.DOC,	a.MaturityDate,	a.PolicyType,IsADB=ISNULL(b.IsADB,'N'),	
a.LateFinePercent,	a.CreatedBy,	a.CreatedDate,b.Name,c.GroupName,b.Mobile,b.EmployeeId,b.Term,b.AppointedDate,
b.Gender,b.NepName,b.Age,b.DOB,b.Address,b.IdNo,'LastPremiumPaidDate'=dateadd(year,-1,a.FUP),b.ExtraPremium ExtraPremium,b.ClientId,b.NomineeName,
tbc.[Nepali Date] NepDOB INTO #temp
FROM tblGroupEndowmentDetails a 
INNER JOIN tblGroupEndowment b
on 
a.PolicyNo=b.PolicyNo
AND
a.RegisterNo=b.RegisterNo 
INNER JOIN tblGroupInformation c 
on a.GroupId=c.GroupId
INNER JOIN dbo.tbl_BSADCalendar AS tbc ON b.DOB=tbc.[English Date]
where a.PolicyNo=@PolicyNo

--DECLARE @TotalSumAssured money,@TotalPaidUp money

--SELECT @TotalSumAssured=SUM(SumAssured) from #temp
--SELECT @TotalPaidUp=SUM(PaidAmount) from #temp

--SELECT @TotalPremium=SUM(Premium) from #temp
--SELECT top 1 @TotalSumAssured AS TotalSumAssured,@TotalPaidUp as TotalPaidUp,@TotalPremium as TotalPremium ,* FROM #temp
--order by PaidDate ASC

SELECT RowId,GroupName,PolicyNo,EmployeeId,GroupId,Name,NepName,DOB,NepDOB,MaturityDate,IsADB,Address,Mobile,IdNo,DOC,Term,SumAssured,BasicPremium,
Premium,ADBPremium,LastPremiumPaidDate,FUP,PolicyStatus,Instalment,PaidAmount,ExtraPremium,ClientId,NomineeName FROM #temp
ORDER BY DOC ASC

DROP TABLE #temp
END

ELSE IF @Flag='ChequeEdit'
BEGIN

IF NOT EXISTS(SELECT * FROM vwAccountPosting WHERE VoucherNo=@VoucherNo)
BEGIN
SELECT 1 CODE ,'Voucher No Not Found' msg,null id
RETURN

END

UPDATE tblCurrentDayPosting SET ChequeNo=@ChequeNo WHERE VoucherNo=@VoucherNo

SELECT 0 CODE,'Cheque Updated Sucessfully' msg,null id
END


ELSE IF @Flag='PrintPolicyDetail'
BEGIN

SELECT Name,NepName,Address,NepAddress,b.BranchName,b.BranchNameNep,a.DOC,a.MaturityDate,a.Premium,a.Term,a.DOB,a.PolicyNo,a.SumAssured,'AgeProof'=c.Value,'AgeProofNep'=c.NepValue,
'Province'=a.ProvinceID,'District'=a.DistrictID,'DistrictNep'=dbo.FN_GetDistrictNep(a.DistrictID,'D')
,'Municipality'=a.MunicipalityID,'MunicipalityNep'=dbo.FN_GetDistrictNep(a.MunicipalityID,'M'),a.WardNo
,a.NepNomineeName,a.NomineeName,a.NomineeWardNo,a.NomineeAddress,a.NepNomineeAddress,'NomDistrict'=a.NomDistrictID,'NomDistrictNep'=dbo.FN_GetDistrictNep(a.NomDistrictID,'D'),a.FatherName,a.MotherName,a.NepFatherName,
a.NepMotherName,NomRelation=d.Value,NepNomRelation=d.NepValue
,NepDueDate=Dbo.FN_GetDueDate('Y',e.FUP),DueDate=Dbo.FN_GetDueDateEng('Y',e.FUP),
FinalPremiumPayingDate=dateadd(year,-1,a.MaturityDate),f.PlanName,f.NepPlanName 

from tblGroupEndowment a
inner join tblBranch b on a.Branch=b.Branch
left join tblStaticDataValue c on c.Id=a.AgeProofDocType
left join tblStaticDataValue d on d.Id=a.NomineeRelationship 
inner join tblGroupEndowmentDetails e on e.PolicyNo=a.PolicyNo
inner join tblplan f on f.planid=a.planid
where a.PolicyNo=@PolicyNo

END



ELSE IF @Flag='GroupSurrenderReport'
BEGIN

SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
--SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupName As [Group Name], @FiscalYear AS [Fiscal Year],@GroupType AS GroupType,
CONVERT(VARCHAR(10),@GroupId,105) AS [Group Master Policy:],
CONVERT(VARCHAR(10),@FromDate,105) AS [Surrender Date From:],
CONVERT(VARCHAR(10),@ToDate,105) AS [Surrender Date To:]
INTO  #tempSearchSurrender

SELECT a.PolicyNo,EmployeeId,a.GroupId,Name,NepName,DOB,DOC=MIN(DOC),Premium=SUM(Premium),SA=SUM(SumAssured),Term=MAX(Term),MaturityDate INTO #tempGroupEndowment
FROM dbo.tblGroupEndowment a

WHERE PolicyStatus='S'
GROUP BY EmployeeId,a.PolicyNo,a.GroupId,Name,NepName,DOB,MaturityDate

select PolicyNo ,Instalment =max(Instalment) into #tblGroupEndowmentDetails  from tblGroupEndowmentDetails group by PolicyNo
SELECT @FromDate=CAST(  convert(varchar, @FromDate, 23) AS DATE )
SELECT @ToDate=CAST(  convert(varchar, @ToDate, 23) AS DATE )
SELECT @DOCDateFrom=CAST(  convert(varchar, @DOCDateFrom, 23) AS DATE )
SELECT @DOCDateTo=CAST(  convert(varchar, @DOCDateTo, 23) AS DATE )
SELECT @IntiDateFrom=CAST(  convert(varchar, @IntiDateFrom, 23) AS DATE )
SELECT @IntiDateTo=CAST(  convert(varchar, @IntiDateTo, 23) AS DATE )
IF @GroupType='Rastasawak'
BEGIN
	IF @DateOption='SurrenderDate'
	BEGIN
		SELECT   ROW_NUMBER() OVER(ORDER BY a.CreatedDate desc ) as SNo,b.PolicyNo,b.EmployeeId,b.Name,b.NepName,CONVERT(VARCHAR(10), b.DOB,103) AS DOB,
		CONVERT(VARCHAR(10), b.DOC,103) AS DOC,b.SA AS SA,b.Premium,Term=CAST(b.Term AS VARCHAR(10)),
		CONVERT(VARCHAR(10),b.MaturityDate,103) AS MaturityDate,a.SurrenderValue AS SurrenderAmount,CONVERT(VARCHAR(10),a.SurrenderDate,103) AS SurrenderDate,
		CONVERT(VARCHAR(10),a.IntimationDate,103) AS IntimationDate
		,a.VoucherNo,a.Tax,a.TotalLoanAmount,NetSurrenderAmount=a.SurrenderValue-a.Tax-a.TotalLoanAmount,a.ClaimId,c.Instalment
		INTO #TempRastasawakSurrender FROM tblGroupSurrender(NOLOCK) a 
		inner join #tempGroupEndowment(NOLOCK) b  
		on a.PolicyNo=b.PolicyNo 
		inner join #tblGroupEndowmentDetails c on a.PolicyNo=c.PolicyNo
		WHERE b.GroupId IN ('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
		AND CAST(a.SurrenderDate AS DATE) BETWEEN ISNULL(CAST(  convert(varchar, @FromDate, 23) AS DATE ),a.SurrenderDate) 
		AND ISNULL(@ToDate,a.SurrenderDate)
		--AND b.DOC BETWEEN ISNULL(@DOCDateFrom,b.DOC) AND ISNULL(@DOCDateTo,b.DOC)
		--AND a.IntimationDate BETWEEN ISNULL (@IntiDateFrom,a.IntimationDate) AND ISNULL(@IntiDateTo, a.IntimationDate)
		AND a.PolicyNo=ISNULL(@PolicyNo,a.PolicyNo)
		
		SELECT * From #TempRastasawakSurrender UNION ALL
			SELECT MAX(SNo) + 1,'Total','','','','','',SUM(SA),SUM(Premium),'','',SUM(SurrenderAmount),'','','',SUM(Tax),SUM(TotalLoanAmount),SUM(NetSurrenderAmount),'',''
			FROM #TempRastasawakSurrender Order By SNo
	END
	ELSE IF @DateOption='IntimationDate'
	BEGIN
		SELECT   ROW_NUMBER() OVER(ORDER BY a.CreatedDate desc ) as SNo,b.PolicyNo,b.EmployeeId,b.Name,b.NepName,CONVERT(VARCHAR(10), b.DOB,103) AS DOB,
		CONVERT(VARCHAR(10), b.DOC,103) AS DOC,b.SA AS SA,b.Premium,Term=CAST(b.Term AS VARCHAR(10)),
		CONVERT(VARCHAR(10),b.MaturityDate,103) AS MaturityDate,a.SurrenderValue AS SurrenderAmount,CONVERT(VARCHAR(10),a.SurrenderDate,103) AS SurrenderDate,
		CONVERT(VARCHAR(10),a.IntimationDate,103) AS IntimationDate
		,a.VoucherNo,a.Tax,a.TotalLoanAmount,NetSurrenderAmount=a.SurrenderValue-a.Tax-a.TotalLoanAmount,a.ClaimId,c.Instalment
		INTO #TempRastasawakSurrenderin FROM tblGroupSurrender(NOLOCK) a 
		inner join #tempGroupEndowment(NOLOCK) b  
		on a.PolicyNo=b.PolicyNo 
		inner join #tblGroupEndowmentDetails c on a.PolicyNo=c.PolicyNo
		WHERE b.GroupId IN ('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
		AND a.IntimationDate BETWEEN ISNULL (@IntiDateFrom,a.IntimationDate) AND ISNULL(@IntiDateTo, a.IntimationDate)
		AND a.PolicyNo=ISNULL(@PolicyNo,a.PolicyNo)
		
		SELECT * From #TempRastasawakSurrenderin UNION ALL
			SELECT MAX(SNo) + 1,'Total','','','','','',SUM(SA),SUM(Premium),'','',SUM(SurrenderAmount),'','','',SUM(Tax),SUM(TotalLoanAmount),SUM(NetSurrenderAmount),'',''
			FROM #TempRastasawakSurrenderin Order By SNo
	END
	
	ELSE IF @DateOption='DOCDate'
		BEGIN
			SELECT   ROW_NUMBER() OVER(ORDER BY a.CreatedDate desc ) as SNo,b.PolicyNo,b.EmployeeId,b.Name,b.NepName,CONVERT(VARCHAR(10), b.DOB,103) AS DOB,
			CONVERT(VARCHAR(10), b.DOC,103) AS DOC,b.SA AS SA,b.Premium,Term=CAST(b.Term AS VARCHAR(10)),
			CONVERT(VARCHAR(10),b.MaturityDate,103) AS MaturityDate,a.SurrenderValue AS SurrenderAmount,CONVERT(VARCHAR(10),a.SurrenderDate,103) AS SurrenderDate,
			CONVERT(VARCHAR(10),a.IntimationDate,103) AS IntimationDate
			,a.VoucherNo,a.Tax,a.TotalLoanAmount,NetSurrenderAmount=a.SurrenderValue-a.Tax-a.TotalLoanAmount,a.ClaimId,c.Instalment
			INTO #TempRastasawakSurrenderdoc FROM tblGroupSurrender(NOLOCK) a 
			inner join #tempGroupEndowment(NOLOCK) b  
			on a.PolicyNo=b.PolicyNo 
			inner join #tblGroupEndowmentDetails c on a.PolicyNo=c.PolicyNo
			WHERE b.GroupId IN ('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
			AND b.DOC BETWEEN ISNULL(@DOCDateFrom,b.DOC) AND ISNULL(@DOCDateTo,b.DOC)
			AND a.PolicyNo=ISNULL(@PolicyNo,a.PolicyNo)
			
			SELECT * From #TempRastasawakSurrenderdoc UNION ALL
				SELECT MAX(SNo) + 1,'Total','','','','','',SUM(SA),SUM(Premium),'','',SUM(SurrenderAmount),'','','',SUM(Tax),SUM(TotalLoanAmount),SUM(NetSurrenderAmount),'',''
				FROM #TempRastasawakSurrenderdoc Order By SNo
		END
ELSE IF @DateOption='SurrenderPaid'
BEGIN
	SELECT   ROW_NUMBER() OVER(ORDER BY a.CreatedDate desc ) as SNo,A.GroupId,b.PolicyNo,b.EmployeeId,b.Name,b.NepName,CONVERT(VARCHAR(10), b.DOB,103) AS DOB,CONVERT(VARCHAR(10), b.DOC,103) AS DOC,b.SA AS SA,b.Premium,Term=CAST(b.Term AS VARCHAR(10)),
	CONVERT(VARCHAR(10),b.MaturityDate,103) AS MaturityDate,a.SurrenderValue AS SurrenderAmount,CONVERT(VARCHAR(10),a.SurrenderDate,103) AS SurrenderDate,
	CONVERT(VARCHAR(10),a.IntimationDate,103) AS IntimationDate,a.VoucherNo,a.Tax,a.TotalLoanAmount LoanAmount,a.CalculatedInterest LoanInterest,a.NetPayable,a.ClaimId,c.Instalment
	INTO #TempGroupSurrenderpaid FROM tblGroupSurrender a 
	inner join #tempGroupEndowment b  
	on a.PolicyNo=b.PolicyNo 
	inner join #tblGroupEndowmentDetails c on a.PolicyNo=c.PolicyNo
	WHERE b.GroupId IN ('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
	AND a.SurrenderPaidDate BETWEEN ISNULL(@FromDate,a.SurrenderPaidDate) AND ISNULL(@ToDate,a.SurrenderPaidDate)
	AND a.PolicyNo=ISNULL(@PolicyNo,a.PolicyNo) 
	
	Select * From #TempGroupSurrenderpaid UNION ALL
	SELECT MAX(SNo) + 1,'Total','','','','','','',SUM(SA),SUM(Premium),'','',SUM(SurrenderAmount),'','','',SUM(Tax),SUM(LoanAmount),SUM(LoanInterest),SUM(NetPayable),'',''
	FROM #TempGroupSurrenderpaid Order By SNo
END
select * from  #tempSearchSurrender

END
ELSE
BEGIN
IF @DateOption='SurrenderDate'
BEGIN
	SELECT   ROW_NUMBER() OVER(ORDER BY a.CreatedDate desc ) as SNo,A.GroupId,b.PolicyNo,b.EmployeeId,b.Name,b.NepName,CONVERT(VARCHAR(10), b.DOB,103) AS DOB,CONVERT(VARCHAR(10), b.DOC,103) AS DOC,b.SA AS SA,b.Premium,Term=CAST(b.Term AS VARCHAR(10)),
	CONVERT(VARCHAR(10),b.MaturityDate,103) AS MaturityDate,a.SurrenderValue AS SurrenderAmount,CONVERT(VARCHAR(10),a.SurrenderDate,103) AS SurrenderDate,
	CONVERT(VARCHAR(10),a.IntimationDate,103) AS IntimationDate,a.VoucherNo,a.Tax,a.TotalLoanAmount LoanAmount,a.CalculatedInterest LoanInterest,a.NetPayable,a.ClaimId,c.Instalment
	INTO #TempGroupSurrender FROM tblGroupSurrender a 
	inner join #tempGroupEndowment b  
	on a.PolicyNo=b.PolicyNo 
	inner join #tblGroupEndowmentDetails c on a.PolicyNo=c.PolicyNo
	WHERE b.GroupId NOT IN ('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
	AND CAST(a.SurrenderDate AS DATE) BETWEEN CAST(ISNULL(@FromDate,a.SurrenderDate)AS DATE) and CAST(ISNULL(@ToDate,a.SurrenderDate)AS DATE)
	--AND b.DOC BETWEEN ISNULL(@DOCDateFrom,b.DOC) AND ISNULL(@DOCDateTo,b.DOC)
	--AND a.IntimationDate BETWEEN ISNULL (@IntiDateFrom,a.IntimationDate) AND ISNULL(@IntiDateTo, a.IntimationDate)
	AND a.PolicyNo=ISNULL(@PolicyNo,a.PolicyNo) 
	
	Select * From #TempGroupSurrender UNION ALL
	SELECT MAX(SNo) + 1,'Total','','','','','','',SUM(SA),SUM(Premium),'','',SUM(SurrenderAmount),'','','',SUM(Tax),SUM(LoanAmount),SUM(LoanInterest),SUM(NetPayable),'',''
	FROM #TempGroupSurrender Order By SNo
END
IF @DateOption='IntimationDate'
BEGIN
	SELECT   ROW_NUMBER() OVER(ORDER BY a.CreatedDate desc ) as SNo,A.GroupId,b.PolicyNo,b.EmployeeId,b.Name,b.NepName,CONVERT(VARCHAR(10), b.DOB,103) AS DOB,CONVERT(VARCHAR(10), b.DOC,103) AS DOC,b.SA AS SA,b.Premium,Term=CAST(b.Term AS VARCHAR(10)),
	CONVERT(VARCHAR(10),b.MaturityDate,103) AS MaturityDate,a.SurrenderValue AS SurrenderAmount,CONVERT(VARCHAR(10),a.SurrenderDate,103) AS SurrenderDate,
	CONVERT(VARCHAR(10),a.IntimationDate,103) AS IntimationDate,a.VoucherNo,a.Tax,a.TotalLoanAmount LoanAmount,a.CalculatedInterest LoanInterest,a.NetPayable,a.ClaimId,c.Instalment
	INTO #TempGroupSurrenderInt FROM tblGroupSurrender a 
	inner join #tempGroupEndowment b  
	on a.PolicyNo=b.PolicyNo 
	inner join #tblGroupEndowmentDetails c on a.PolicyNo=c.PolicyNo
	WHERE b.GroupId NOT IN ('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
	AND a.IntimationDate BETWEEN ISNULL (@IntiDateFrom,a.IntimationDate) AND ISNULL(@IntiDateTo, a.IntimationDate)
	AND a.PolicyNo=ISNULL(@PolicyNo,a.PolicyNo) 
	
	Select * From #TempGroupSurrenderInt UNION ALL
	SELECT MAX(SNo) + 1,'Total','','','','','','',SUM(SA),SUM(Premium),'','',SUM(SurrenderAmount),'','','',SUM(Tax),SUM(LoanAmount),SUM(LoanInterest),SUM(NetPayable),'',''
	FROM #TempGroupSurrenderInt Order By SNo
END
IF @DateOption='DOCDate'
BEGIN
	SELECT   ROW_NUMBER() OVER(ORDER BY a.CreatedDate desc ) as SNo,A.GroupId,b.PolicyNo,b.EmployeeId,b.Name,b.NepName,CONVERT(VARCHAR(10), b.DOB,103) AS DOB,CONVERT(VARCHAR(10), b.DOC,103) AS DOC,b.SA AS SA,b.Premium,Term=CAST(b.Term AS VARCHAR(10)),
	CONVERT(VARCHAR(10),b.MaturityDate,103) AS MaturityDate,a.SurrenderValue AS SurrenderAmount,CONVERT(VARCHAR(10),a.SurrenderDate,103) AS SurrenderDate,
	CONVERT(VARCHAR(10),a.IntimationDate,103) AS IntimationDate,a.VoucherNo,a.Tax,a.TotalLoanAmount LoanAmount,a.CalculatedInterest LoanInterest,a.NetPayable,a.ClaimId,c.Instalment
	INTO #TempGroupSurrenderdoc FROM tblGroupSurrender a 
	inner join #tempGroupEndowment b  
	on a.PolicyNo=b.PolicyNo 
	inner join #tblGroupEndowmentDetails c on a.PolicyNo=c.PolicyNo
	WHERE b.GroupId NOT IN ('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
	AND b.DOC BETWEEN ISNULL(@DOCDateFrom,b.DOC) AND ISNULL(@DOCDateTo,b.DOC)
	AND a.PolicyNo=ISNULL(@PolicyNo,a.PolicyNo) 
	
	Select * From #TempGroupSurrenderdoc UNION ALL
	SELECT MAX(SNo) + 1,'Total','','','','','','',SUM(SA),SUM(Premium),'','',SUM(SurrenderAmount),'','','',SUM(Tax),SUM(LoanAmount),SUM(LoanInterest),SUM(NetPayable),'',''
	FROM #TempGroupSurrenderdoc Order By SNo
END
IF @DateOption='SurrenderPaid'
BEGIN
	SELECT   ROW_NUMBER() OVER(ORDER BY a.CreatedDate desc ) as SNo,A.GroupId,b.PolicyNo,b.EmployeeId,b.Name,b.NepName,CONVERT(VARCHAR(10), b.DOB,103) AS DOB,CONVERT(VARCHAR(10), b.DOC,103) AS DOC,b.SA AS SA,b.Premium,Term=CAST(b.Term AS VARCHAR(10)),
	CONVERT(VARCHAR(10),b.MaturityDate,103) AS MaturityDate,a.SurrenderValue AS SurrenderAmount,CONVERT(VARCHAR(10),a.SurrenderDate,103) AS SurrenderDate,
	CONVERT(VARCHAR(10),a.IntimationDate,103) AS IntimationDate,a.VoucherNo,a.Tax,a.TotalLoanAmount LoanAmount,a.CalculatedInterest LoanInterest,a.NetPayable,a.ClaimId,c.Instalment
	INTO #TempGroupSurrenderpayment FROM tblGroupSurrender a 
	inner join #tempGroupEndowment b  
	on a.PolicyNo=b.PolicyNo 
	inner join #tblGroupEndowmentDetails c on a.PolicyNo=c.PolicyNo
	WHERE b.GroupId NOT IN ('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
	AND a.SurrenderPaidDate BETWEEN ISNULL(@FromDate,a.SurrenderPaidDate) AND ISNULL(@ToDate,a.SurrenderPaidDate)
	AND a.PolicyNo=ISNULL(@PolicyNo,a.PolicyNo) 
	
	Select * From #TempGroupSurrenderpayment UNION ALL
	SELECT MAX(SNo) + 1,'Total','','','','','','',SUM(SA),SUM(Premium),'','',SUM(SurrenderAmount),'','','',SUM(Tax),SUM(LoanAmount),SUM(LoanInterest),SUM(NetPayable),'',''
	FROM #TempGroupSurrenderpayment Order By SNo
END
select * from  #tempSearchSurrender


END

END


ELSE IF @Flag='GroupDeathReport'
BEGIN


SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId

IF @GroupType='Select Group Type'
SET @GroupType='All Group Report'

SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupName As [Group Name], @FiscalYear AS [Fiscal Year],@GroupType AS GroupType,
CONVERT(VARCHAR(10),@GroupId,105) AS [Group Master Policy:],
CONVERT(VARCHAR(10),@FromDate,105) AS [Death From:],
CONVERT(VARCHAR(10),@ToDate,105) AS [Death Date To:]
INTO  #tempSearchDeath


SELECT PolicyNo,EmployeeId,GroupId,Name,NepName,DOB,DOC=MIN(DOC),Premium=SUM(Premium),SA=SUM(SumAssured),Term=MAX(Term),MaturityDate INTO #tempGroupEndowmentDeath
FROM dbo.tblGroupEndowment
WHERE PolicyStatus='D'
GROUP BY EmployeeId,PolicyNo,GroupId,Name,NepName,DOB,MaturityDate

select PolicyNo ,Instalment =max(Instalment) into #tempGroupEndowmentDetails  from tblGroupEndowmentDetails group by PolicyNo

IF @GroupType='Rastasawak'
BEGIN
SELECT   ROW_NUMBER() OVER(ORDER BY a.CreatedDate desc) as SNo,a.GroupId,b.PolicyNo,b.EmployeeId,b.Name,b.NepName,CONVERT(VARCHAR(10), b.DOB,103) AS DOB,b.SA AS SA,
b.Premium,CONVERT(VARCHAR(10), b.DOC,103) AS DOC,CONVERT(VARCHAR(10),b.MaturityDate,103) AS MaturityDate,a.TotalBonus AS Bonus,a.TotalClaimAmount AS ClaimAmount,a.LoanAmount
--,NetClaimAmount=a.TotalClaimAmount-a.LoanAmount,
,InterestOnLoanAmount = a.CalculatedInterest
,TotalClaimAmount = b.SA +a.TotalBonus
,NetClaimAmount=b.SA+a.TotalBonus-ISNULL(a.LoanAmount, 0)-ISNULL(a.CalculatedInterest,0),
CONVERT(VARCHAR(10),a.DeathDate,103) AS DeathDate,CONVERT(VARCHAR(10),a.IntimationDate,103) AS IntimationDate,CONVERT(VARCHAR(10),a.TerminationDate,103) AS TerminationDate,a.VoucherNo,a.ClaimId,c.Instalment
INTO #TempRastasawakDeath FROM tblGroupDeathClaim a 
inner join #tempGroupEndowmentDeath b 
on a.PolicyNo=b.PolicyNo 
inner join #tempGroupEndowmentDetails c on a.PolicyNo=c.PolicyNo
WHERE a.GroupId  IN ('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
AND a.PolicyNo=ISNULL(@PolicyNo,a.PolicyNo)
AND CASE WHEN @DateOption='DeathDate' THEN CAST(a.DeathDate AS DATE)
WHEN @DateOption='DeathRegister' THEN CAST(a.CreatedDate AS DATE) 
WHEN @Dateoption='DeathPaid' THEN CAST(a.PaidDate AS DATE)
ELSE b.DOC END
 BETWEEN ISNULL(@FromDate,a.DeathDate) AND ISNULL(@ToDate,a.DeathDate)
--AND a.PolicyStatus = '1'

Select * From #TempRastasawakDeath UNION ALL
	SELECT MAX(SNo) + 1,'Total','','','','','',SUM(SA),SUM(Premium),'','',SUM(Bonus),SUM(ClaimAmount),SUM(LoanAmount)
	,SUM(InterestOnLoanAmount),SUM(TotalClaimAmount)
	,SUM(NetClaimAmount),'','','','','',''
	FROM #TempRastasawakDeath Order By SNo

select * from  #tempSearchDeath
END
IF @GroupType='Group'
BEGIN
SELECT   ROW_NUMBER() OVER(ORDER BY a.CreatedDate desc) as SNo,a.GroupId,b.PolicyNo,b.EmployeeId,b.Name,b.NepName,CONVERT(VARCHAR(10), b.DOB,103) AS DOB,b.SA AS SA,
b.Premium,CONVERT(VARCHAR(10), b.DOC,103) AS DOC,CONVERT(VARCHAR(10),b.MaturityDate,103) AS MaturityDate,a.TotalBonus AS Bonus,a.TotalClaimAmount AS ClaimAmount,a.LoanAmount
--,NetClaimAmount=a.TotalClaimAmount-a.LoanAmount,
,InterestOnLoanAmount = a.CalculatedInterest
,TotalClaimAmount = b.SA +a.TotalBonus
,NetClaimAmount=b.SA+a.TotalBonus-ISNULL(a.LoanAmount, 0)-ISNULL(a.CalculatedInterest,0),
CONVERT(VARCHAR(10),a.DeathDate,103) AS DeathDate,CONVERT(VARCHAR(10),a.IntimationDate,103) AS IntimationDate,CONVERT(VARCHAR(10),a.TerminationDate,103) AS TerminationDate,a.VoucherNo,a.ClaimId,c.Instalment
INTO #TempGroupDeath FROM tblGroupDeathClaim a 
inner join #tempGroupEndowmentDeath b 
on a.PolicyNo=b.PolicyNo 
inner join #tempGroupEndowmentDetails c on a.PolicyNo=c.PolicyNo
WHERE a.GroupId  NOT IN ('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
AND  CASE WHEN @DateOption='DeathDate' THEN CAST(a.DeathDate AS DATE)
WHEN @DateOption='DeathRegister' THEN CAST(a.CreatedDate AS DATE) 
WHEN @Dateoption='DeathPaid' THEN CAST(a.PaidDate AS DATE)
ELSE b.DOC END
 BETWEEN ISNULL(@FromDate,a.DeathDate) AND ISNULL(@ToDate,a.DeathDate)
AND a.PolicyNo=ISNULL(@PolicyNo,a.PolicyNo)


Select * From #TempGroupDeath UNION ALL
	SELECT MAX(SNo) + 1,'Total','','','','','',SUM(SA),SUM(Premium),'','',SUM(Bonus),SUM(ClaimAmount),SUM(LoanAmount)
	,SUM(InterestOnLoanAmount),SUM(TotalClaimAmount)
	,SUM(NetClaimAmount),'','','','','',''
	FROM #TempGroupDeath Order By SNo

select * from  #tempSearchDeath
END
ELSE
BEGIN
SELECT   ROW_NUMBER() OVER(ORDER BY a.CreatedDate desc) as SNo,a.GroupId,b.PolicyNo,b.EmployeeId,b.Name,b.NepName,CONVERT(VARCHAR(10), b.DOB,103) AS DOB,b.SA AS SA,
b.Premium,CONVERT(VARCHAR(10), b.DOC,103) AS DOC,CONVERT(VARCHAR(10),b.MaturityDate,103) AS MaturityDate,a.TotalBonus AS Bonus,a.TotalClaimAmount AS ClaimAmount,a.LoanAmount
--,NetClaimAmount=a.TotalClaimAmount-a.LoanAmount,
,InterestOnLoanAmount = a.CalculatedInterest
,TotalClaimAmount = b.SA +a.TotalBonus
,NetClaimAmount=b.SA+a.TotalBonus-ISNULL(a.LoanAmount, 0)-ISNULL(a.CalculatedInterest,0),
CONVERT(VARCHAR(10),a.DeathDate,103) AS DeathDate,CONVERT(VARCHAR(10),a.IntimationDate,103) AS IntimationDate,CONVERT(VARCHAR(10),a.TerminationDate,103) AS TerminationDate,a.VoucherNo,a.ClaimId,c.Instalment
INTO #TempGroupAllDeath FROM tblGroupDeathClaim a 
inner join #tempGroupEndowmentDeath b 
on a.PolicyNo=b.PolicyNo 
inner join #tempGroupEndowmentDetails c on a.PolicyNo=c.PolicyNo
WHERE CASE WHEN @DateOption='DeathDate' THEN CAST(a.DeathDate AS DATE)
WHEN @DateOption='DeathRegister' THEN CAST(a.CreatedDate AS DATE) 
WHEN @Dateoption='DeathPaid' THEN CAST(a.PaidDate AS DATE)
ELSE b.DOC END
 BETWEEN ISNULL(@FromDate,a.DeathDate) AND ISNULL(@ToDate,a.DeathDate)
AND a.PolicyNo=ISNULL(@PolicyNo,a.PolicyNo)
--AND a.PolicyStatus = '1'

Select * From #TempGroupAllDeath UNION ALL
	SELECT MAX(SNo) + 1,'Total','','','','','',SUM(SA),SUM(Premium),'','',SUM(Bonus),SUM(ClaimAmount),SUM(LoanAmount)
	,SUM(InterestOnLoanAmount),SUM(TotalClaimAmount)
	,SUM(NetClaimAmount),'','','','','',''
	FROM #TempGroupAllDeath Order By SNo

select * from  #tempSearchDeath
END 



END

ELSE IF @Flag='MaturityForecastingReport' ------copo
BEGIN

-- SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupId As [Group Id],
-- CONVERT(VARCHAR(10),@FromDate,105) AS [ Date From:],
-- CONVERT(VARCHAR(10),@ToDate,105) AS [ Date To:]
-- INTO  #tempMaturityForecastingReport1


SELECT ROW_NUMBER() OVER (ORDER BY PolicyNo) AS SN, PolicyNo,Branch,Name,NepName,GroupId,DOB=CONVERT(VARCHAR(10),DOB,103),DOC=CONVERT(VARCHAR(10),MIN(DOC),103),
SumAssured=SUM(SumAssured),
Term=MAX(Term),Instalment =MAX(Instalment),Premium=SUM(Premium),MaturityDate=CONVERT(VARCHAR(10),MaturityDate,103),
TotalPolicy=COUNT(PolicyNo),RemainingDayToMature=DATEDIFF(DAY,GETDATE(),MaturityDate),PolicyStatus 
---INTO #temMaturityForecast
-- FROM dbo.tblGroupEndowment 
FROM dbo.view_copo_GroupEndowment 

WHERE GroupId=@GroupId
AND PolicyStatus='A' 
AND policyNo IS NOT NULL
AND convert(Date,MaturityDate,103) BETWEEN convert(Date,@FromDate,103) AND convert(Date,@ToDate,103)
GROUP BY PolicyNo,Branch,Name,NepName,GroupId,DOB,MaturityDate,PolicyStatus 
ORDER BY PolicyNo

-- SELECT * FROM #tempMaturityForecastingReport1
-- DROP TABLE #tempMaturityForecastingReport1

RETURN
END


ELSE IF @Flag='GroupAllClaimReport'
BEGIN

SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupId As [Group Id],

CONVERT(VARCHAR(10),@FromDate,105) AS [ Date From:],
CONVERT(VARCHAR(10),@ToDate,105) AS [ Date To:]
INTO  #tempGroupAllClaimReport


SELECT PolicyNo,GroupId,Name,DOB,DOC=MIN(DOC),Term=MAX(Term),SA=SUM(SumAssured),Premium=SUM(Premium),PolicyStatus,TotalPolicy=COUNT(PolicyNo) 
INTO #temptblGroupEndowment 
FROM dbo.tblGroupEndowment WHERE GroupId=ISNULL(@GroupId,GroupId)
GROUP BY PolicyNo,GroupId,Name,DOB,PolicyStatus

------------------Terminate Policy-----------------------------
SELECT PolicyNo,GroupId,DOB,DOC=MIN(DOC),Term=MAX(Term),Name,SA=SUM(SumAssured),Premium=SUM(Premium),PolicyStatus,TerminationDate AS CreatedDate,TerminateBy AS CreatedBy,TotalPolicy=COUNT(PolicyNo)
INTO #tempTerminateData
FROM dbo.tblGroupEndowment 
WHERE TerminationDate BETWEEN @FromDate AND @ToDate
AND  PolicyStatus='T'
AND GroupId=ISNULL(@GroupId,GroupId)
GROUP BY  PolicyNo,GroupId,Name,DOB,PolicyStatus,TerminationDate,TerminateBy
--------------------------------------------------------

------------------TRANSFER Policy-------------------------------------

SELECT PolicyNo,DOB,Name,GroupId,DOC=MIN(DOC),Term=MAX(Term),SA=SUM(SumAssured),Premium=SUM(Premium),TransferDate AS CreatedDate,TransferBy AS CreatedBy,PolicyStatus,TotalPolicy=COUNT(PolicyNo)
INTO #tempTransferData
FROM dbo.tblGroupEndowment 
WHERE TransferDate BETWEEN @FromDate AND @ToDate
AND  PolicyStatus='I'
AND GroupId=ISNULL(@GroupId,GroupId)
GROUP BY  PolicyNo,GroupId,Name,DOB,PolicyStatus,TransferDate,TransferBy

-----------------DeathClaim---------------------------------------------------------

SELECT A.PolicyNo,B.DOB,B.Name,B.GroupId,B.DOC,B.Term,B.SA,B.Premium,A.CreatedDate,A.CreatedBy,b.PolicyStatus,b.TotalPolicy INTO #temptblGroupDeathClaim
FROM dbo.tblGroupDeathClaim A 
INNER JOIN #temptblGroupEndowment B 
ON A.PolicyNo=B.PolicyNo
WHERE CAST(PaidDate AS DATE) BETWEEN @FromDate AND @ToDate
AND A.GroupId=ISNULL(@GroupId,A.GroupId)

---------------------------------maturityClaim-----------------------------------

SELECT A.PolicyNo,B.DOB,B.Name,B.GroupId,B.DOC,B.Term,B.SA,B.Premium,A.CreatedDate,A.CreatedBy,b.PolicyStatus,b.TotalPolicy INTO #temptblGroupMaturity
FROM dbo.tblGroupMaturity A 
INNER JOIN #temptblGroupEndowment B 
ON A.PolicyNo=B.PolicyNo
WHERE CAST(A.PaidDate AS DATE) BETWEEN '2021-01-01' AND '2022-01-01'
AND A.GroupId=ISNULL(@GroupId,A.GroupId)

----------------------------

--surrenderClaim

SELECT A.PolicyNo,B.DOB,B.Name,B.GroupId,B.DOC,B.Term,B.SA,B.Premium,A.CreatedDate,A.CreatedBy,b.PolicyStatus,b.TotalPolicy INTO #temptblGroupSurrender
FROM dbo.tblGroupSurrender A 
INNER JOIN #temptblGroupEndowment B 
ON A.PolicyNo=B.PolicyNo
WHERE CAST(A.SurrenderPaidDate AS DATE) BETWEEN @FromDate AND @ToDate
AND A.GroupId=ISNULL(@GroupId,A.GroupId)

----------------------------

CREATE TABLE #ClaimAllReport
(
SN BIGINT IDENTITY(1,1),
PolicyNo VARCHAR(100),
DOB DATE,
DOC DATE,
Term BIGINT,
Name VARCHAR(100),
GroupId VARCHAR(100),
SA MONEY,
Premium MONEY,
CreatedDate DATE,
CreatedBy VARCHAR(100),
PolicyStatus VARCHAR(100),
TotalPolicy VARCHAR(100)
)


INSERT INTO #ClaimAllReport
(
    PolicyNo,
    DOB,
	Name,
	GroupId,
	DOC,
	Term,
    SA,
    Premium,
    CreatedDate,
    CreatedBy,
    PolicyStatus,
	TotalPolicy
)

SELECT PolicyNo,DOB,Name,GroupId,DOC,Term,SA,Premium,CreatedDate,CreatedBy,PolicyStatus,TotalPolicy FROM #tempTerminateData
UNION ALL SELECT PolicyNo,DOB,Name,GroupId,DOC,Term,SA,Premium,CreatedDate,CreatedBy,PolicyStatus,TotalPolicy FROM #tempTransferData
UNION ALL SELECT PolicyNo,DOB,Name,GroupId,DOC,Term,SA,Premium,CreatedDate,CreatedBy,PolicyStatus,TotalPolicy FROM #temptblGroupDeathClaim
UNION ALL SELECT PolicyNo,DOB,Name,GroupId,DOC,Term,SA,Premium,CreatedDate,CreatedBy,PolicyStatus,TotalPolicy FROM #temptblGroupMaturity
UNION ALL SELECT PolicyNo,DOB,Name,GroupId,DOC,Term,SA,Premium,CreatedDate,CreatedBy,PolicyStatus,TotalPolicy FROM #temptblGroupSurrender


SELECT ROW_NUMBER() OVER (ORDER BY PolicyNo) AS SN,GroupId,DOC=CONVERT(VARCHAR(10),DOC,103),Term,PolicyNo,DOB=CONVERT(VARCHAR(10),DOB,103),Name,SA,Premium,CreatedDate=CONVERT(VARCHAR(10),CreatedDate,103),CreatedBy,PolicyStatus,TotalPolicy 
INTO #ClaimAllReport1
FROM #ClaimAllReport


SELECT SN,PolicyNo,DOB,Name,GroupId,DOC,Term,SA,Premium,CreatedDate,CreatedBy,PolicyStatus,TotalPolicy FROM #ClaimAllReport1 UNION ALL
SELECT MAX(SN)+1,'Total','','','','','',SUM(SA),SUM(Premium),'','','','' FROM #ClaimAllReport1 ORDER BY SN

SELECT * FROM #tempGroupAllClaimReport

DROP TABLE #temptblGroupEndowment
DROP TABLE #tempTerminateData
DROP TABLE #tempTransferData
DROP TABLE #temptblGroupDeathClaim
DROP TABLE #temptblGroupMaturity
DROP TABLE #temptblGroupSurrender
DROP TABLE #ClaimAllReport
DROP TABLE #ClaimAllReport1
DROP TABLE #tempGroupAllClaimReport

RETURN
END


ELSE IF @Flag='GroupMaturityReport'
BEGIN


SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupName As [Group Name], @FiscalYear AS [Fiscal Year],@GroupType AS GroupType,
CONVERT(VARCHAR(10),@GroupId,105) AS [Group Master Policy:],
CONVERT(VARCHAR(10),@FromDate,105) AS [Maturity Date From:],
CONVERT(VARCHAR(10),@ToDate,105) AS [Maturity Date To:]
INTO  #tempSearchMaturity


SELECT a.PolicyNo,EmployeeId,a.GroupId,Name,NepName,DOB,DOC=MIN(DOC),Premium=SUM(Premium),SA=SUM(SumAssured),Term=MAX(Term),MaturityDate INTO #tempGroupEndowmentMaturity
FROM dbo.tblGroupEndowment a
--left join tblGroupPolicyLoanDetail b on a.PolicyNo=b.PolicyNo
--WHERE PolicyStatus='M'
GROUP BY EmployeeId,a.PolicyNo,a.GroupId,Name,NepName,DOB,MaturityDate


IF @GroupType='Rastasawak'
BEGIN
SELECT   ROW_NUMBER() OVER(ORDER BY a.CreatedDate desc) as SNo,b.PolicyNo,b.EmployeeId,b.Name,b.NepName,CONVERT(VARCHAR(10), b.DOB,103) AS DOB,b.SA AS SA,
b.Premium,CONVERT(VARCHAR(10), b.DOC,103) AS DOC,CONVERT(VARCHAR(10),b.MaturityDate,103) AS MaturityDate,a.TotalBonus AS Bonus,a.TotalTax,a.TotalClaimAmount AS ClaimAmount,a.LoanAmount,a.CalculatedInterest,NetClaimAmount=a.TotalClaimAmount-a.TotalTax-a.LoanAmount-a.CalculatedInterest,
CONVERT(VARCHAR(10),a.ClaimDate,103) AS ClaimDate,a.VoucherNo,a.ClaimId 
INTO #TempRastasawakMaturity FROM dbo.tblGroupMaturity a 
inner join #tempGroupEndowmentMaturity b 
on a.PolicyNo=b.PolicyNo 
WHERE a.GroupId  IN ('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
 AND CASE WHEN @DateOption='MaturityDate' THEN CAST(b.MaturityDate AS DATE)
WHEN @DateOption='MaturityRegister' THEN CAST(a.CreatedDate AS DATE) 
WHEN @Dateoption='MaturityPaid' THEN CAST(a.PaidDate AS DATE)
ELSE b.DOC END
 BETWEEN ISNULL(@FromDate,b.MaturityDate) AND ISNULL(@ToDate,b.MaturityDate)
AND a.PolicyNo=ISNULL(@PolicyNo,a.PolicyNo)

--AND a.PolicyStatus = '1'

Select * From #TempRastasawakMaturity UNION ALL
	SELECT MAX(SNo) + 1,'Total','','','','',SUM(SA),SUM(Premium),'','',SUM(Bonus),SUM(TotalTax),SUM(ClaimAmount),SUM(LoanAmount),SUM(CalculatedInterest),SUM(NetClaimAmount),'','',''
	FROM #TempRastasawakMaturity Order By SNo

select * from  #tempSearchMaturity

END
ELSE
BEGIN


SELECT   ROW_NUMBER() OVER(ORDER BY a.CreatedDate desc) as SNo,A.GroupId,b.PolicyNo,b.EmployeeId,b.Name,b.NepName,CONVERT(VARCHAR(10), b.DOB,103) AS DOB,b.SA AS SA,
b.Premium,CONVERT(VARCHAR(10), b.DOC,103) AS DOC,CONVERT(VARCHAR(10),b.MaturityDate,103) AS MaturityDate,a.TotalBonus AS Bonus,a.TotalTax,a.TotalClaimAmount AS ClaimAmount,a.LoanAmount,a.CalculatedInterest,NetClaimAmount=a.TotalClaimAmount-a.TotalTax-a.LoanAmount-a.CalculatedInterest,
CONVERT(VARCHAR(10),a.ClaimDate,103) AS ClaimDate,a.VoucherNo,a.ClaimId 
INTO #TempGroupMaturity FROM dbo.tblGroupMaturity a 
left join #tempGroupEndowmentMaturity b 
on a.PolicyNo=b.PolicyNo 
WHERE a.GroupId NOT IN ('GE1001','GE1002','GE1003','GE1004','GE1005','GE1022')
AND CASE WHEN @DateOption='MaturityDate' THEN CAST(b.MaturityDate AS DATE)
WHEN @DateOption='MaturityRegister' THEN CAST(a.CreatedDate AS DATE) 
WHEN @Dateoption='MaturityPaid' THEN CAST(a.PaidDate AS DATE)
ELSE b.DOC END
 BETWEEN ISNULL(@FromDate,b.MaturityDate) AND ISNULL(@ToDate,b.MaturityDate)
AND a.PolicyNo=ISNULL(@PolicyNo,a.PolicyNo)
--AND a.PolicyStatus = '1'

Select * From #TempGroupMaturity UNION ALL
	SELECT MAX(SNo) + 1,'Total','','','','','',SUM(SA),SUM(Premium),'','',SUM(Bonus),SUM(TotalTax),SUM(ClaimAmount),SUM(LoanAmount),SUM(CalculatedInterest),SUM(NetClaimAmount),'','',''
	FROM #TempGroupMaturity Order By SNo

select * from  #tempSearchMaturity

END



END



ELSE IF @flag='rptGroupPolicyLoanRepayment'
BEGIN


SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn', @FiscalYear AS [Fiscal Year],
CONVERT(VARCHAR(10),@FromDate,105) AS [ Date From:],
CONVERT(VARCHAR(10),@ToDate,105) AS [ Date To:]
INTO  #temprptGroupPolicyLoanRepayment


SELECT DISTINCT Name,PolicyNo INTO #AA FROM dbo.tblGroupEndowment




	SELECT ROW_NUMBER() OVER(ORDER BY a.CreatedDate ASC) AS RowNo,a.PolicyNo,id.Name AS FullName,
	a.LoanId,LoanDate=CONVERT(VARCHAR(10),b.LoanDate,121),b.LoanAmount,a.Instalment,a.DuePrincipal,a.PaidPrincipal,a.RemainingPrincipal,a.PaidInterest,a.RemainingInterest,
	Cash=CASE WHEN dbo.FN_GetGlCode(a.PaymentFrom)=171 THEN a.PaidAmount ELSE 0 END,
	Cheque=CASE WHEN dbo.FN_GetGlCode(a.PaymentFrom)=172 THEN a.PaidAmount ELSE 0 END,
	Bank=CASE WHEN dbo.FN_GetGlCode(a.PaymentFrom) in ('179','177') THEN a.PaidAmount ELSE 0 END,PaymentFrom=dbo.FN_GetAccountName(a.PaymentFrom)
	,b.Status ,PaidDate=CONVERT(VARCHAR(10),a.PaidDate,121),[Tran/Cheque Date]=CONVERT(VARCHAR(10),a.ChequeDate,121),a.VoucherNo INTO #GroupPolicyLoanRepayment
	FROM dbo.tblGroupPolicyLoanPaid a (NOLOCK)
	INNER JOIN dbo.tblGroupPolicyLoanDetail b (NOLOCK) ON b.PolicyNo = a.PolicyNo AND b.LoanId = a.LoanId
	--INNER JOIN dbo.tblGroupEndowmentDetails pd (NOLOCK) ON pd.PolicyNo = a.PolicyNo 
	INNER JOIN dbo.#AA id (NOLOCK) ON id.PolicyNo = a.PolicyNo 
	--WHERE a.PaidDate BETWEEN @fromDate AND @toDate AND a.PolicyNo=ISNULL(@policyNo,a.PolicyNo) AND 
	WHERE CAST(a.PaidDate AS DATE) BETWEEN @fromDate AND @toDate AND a.PolicyNo=ISNULL(@policyNo,a.PolicyNo)  
	AND a.Remarks NOT IN ('Paid From Maturity Amount','Paid From Death Amount','Paid From Surrender Amount')
	--AND a.Branch= CASE WHEN @branch IS NULL AND dbo.FN_GetBranch(@user)='300' THEN a.Branch ELSE @branch END ORDER BY a.PaidDate ASC


	SELECT * FROM #GroupPolicyLoanRepayment 
  UNION ALL SELECT Max(RowNo)+1,'Total','','','',SUM(LoanAmount),'',SUM(DuePrincipal),SUM(PaidPrincipal),SUM(RemainingPrincipal),SUM(PaidInterest),SUM(RemainingInterest),SUM(Cash),SUM(Cheque),SUM(Bank),
  '','','','','' FROM #GroupPolicyLoanRepayment ORDER BY RowNo ASC
  SELECT * FROM #temprptGroupPolicyLoanRepayment

	DROP TABLE #temprptGroupPolicyLoanRepayment
	DROP TABLE #GroupPolicyLoanRepayment
END
ELSE IF @flag='rptGroupPolicyLoanPayment'
BEGIN
	
	SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn', @FiscalYear AS [Fiscal Year],
CONVERT(VARCHAR(10),@FromDate,105) AS [ Date From:],
CONVERT(VARCHAR(10),@ToDate,105) AS [ Date To:]
INTO  #temprptGroupPolicyLoanPayment

	SELECT  Name,PolicyNo,DOC=MAX(DOC),Term=MAX(Term)  INTO #GroupEndowment FROM dbo.tblGroupEndowment
	GROUP BY PolicyNo,Name

    SELECT  PolicyNo,SA=SUM(SumAssured),Premium=SUM(Premium),FUP,Branch INTO #GroupEndowmentDetails FROM dbo.tblGroupEndowmentDetails
	GROUP BY PolicyNo,FUP,Branch

	SELECT ROW_NUMBER() OVER(ORDER BY a.CreatedDate ASC) AS RowNo,
	CAST(B.Branch AS VARCHAR) Branch,
	B.PolicyNo,
	A.LoanId,
	'Name'=C.Name,
	'Premium'=CAST(B.Premium AS INT),
	'SA'=CAST(B.SA AS INT),	
	'DOC'=CONVERT(VARCHAR(10),C.DOC,103),
	'FUP'=CONVERT(VARCHAR(10),b.FUP,103),
	PlanID=1,C.Term AS 'PolicyTerm',
	PayMode='Y',
	'Initial Loan Date'=CONVERT(VARCHAR(10),A.LoanDate,103),
	'Loan Amount' = ISNULL(A.LoanAmount,0),
	'Last Paid Date'=CONVERT(VARCHAR(10),ISNULL(A.LastPaidDate,A.LoanDate),103),
	'Principal Amount' = ISNULL(A.PrincipalAmount,A.LoanAmount),
	A.Status,
	A.ServiceCharge,
	CAST(STUFF(LoanId, 1, PATINDEX('%[0-9]%', LoanId)-1, '') AS BIGINT) AS ShortIndex
	INTO #JJJ FROM tblGroupPolicyLoanDetail A  (NOLOCK)
	INNER JOIN dbo.#GroupEndowmentDetails B (NOLOCK) ON B.PolicyNo = A.PolicyNo
	INNER JOIN dbo.#GroupEndowment C (NOLOCK) ON C.PolicyNo = A.PolicyNo
	WHERE  --AND B.CurrentStatus = 'M'
	ISNULL(A.LoanAmount,0)>0 
	
	AND A.LoanDate BETWEEN @fromDate AND @toDate 
	AND B.PolicyNo=ISNULL(@policyNo,B.PolicyNo)
	AND A.Status=ISNULL(@Status,A.Status)

	SELECT RowNo,Branch,PolicyNo,LoanId,Name,Premium,SA,DOC,FUP,PlanID,PolicyTerm,PayMode,[Initial Loan Date],
		[Loan Amount],[Last Paid Date],[Principal Amount],	Status,ServiceCharge	 
	FROM #JJJ 
	UNION ALL SELECT MAX(RowNo)+1,'Total','','','',SUM(Premium),SUM(SA),'','','','','','',SUM([Loan Amount]),'',SUM([Principal Amount]),'',SUM(ServiceCharge) 
	FROM #JJJ ORDER BY RowNo

	SELECT * FROM #temprptGroupPolicyLoanPayment

	DROP TABLE #JJJ
	DROP TABLE #GroupEndowment
	DROP TABLE #GroupEndowmentDetails

END





ELSE IF @Flag='GroupFPSummaryReport'
BEGIN

SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
--SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',ISNULL(@GroupName,'ALL GROUP REPORT') As [Group Name], @FiscalYear AS [Fiscal Year],
CONVERT(VARCHAR(100),@GroupId,105) AS [Group Code:],
CONVERT(VARCHAR(10),@FromDate,105) AS [DOC Date From:],
CONVERT(VARCHAR(10),@ToDate,105) AS [DOC Date To:]
INTO  #tempSearchFPSummaryReport


SELECT ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS SN, GED.GroupId,GI.GroupName,TotalPolicy=COUNT(GED.PolicyNo),TotalSA=SUM(SumAssured),TotalPremium=SUM(GED.Premium)
INTO #GroupFP
FROM tblGroupEndowmentDetails GED
INNER JOIN  tblGroupInformation GI 
ON GED.GroupId=GI.groupid 
WHERE GED.GroupId=ISNULL(@GroupId,GED.GroupId)
AND GED.DOC BETWEEN @FromDate AND @ToDate
AND PolicyStatus NOT IN('Cancel')
GROUP BY GED.GroupId,GI.GroupName
ORDER BY GroupId

ALTER TABLE #GroupFP 
ALTER COLUMN GroupId VARCHAR(100)

ALTER TABLE #GroupFP
ALTER COLUMN TotalPolicy INT

SELECT * FROM #GroupFP
UNION ALL SELECT MAX(SN+1),'Total','',SUM(TotalPolicy),SUM(TotalSA),SUM(TotalPremium) FROM #GroupFP
ORDER BY SN

SELECT * FROM  #tempSearchFPSummaryReport
DROP TABLE #GroupFP

DROP TABLE #tempSearchFPSummaryReport
RETURN



END

ELSE IF @Flag='GroupPolicyTypeReport'
BEGIN

SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
--SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',ISNULL(@GroupName,'ALL GROUP REPORT') As [Group Name], @FiscalYear AS [Fiscal Year],
CONVERT(VARCHAR(100),@GroupId,105) AS [Group Code:],
CONVERT(VARCHAR(10),@FromDate,105) AS [DOC Date From:],
CONVERT(VARCHAR(10),@ToDate,105) AS [DOC Date To:]
INTO  #tempSearchPSummaryReport


SELECT ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS SN, GED.GroupId,GI.GroupName,GED.PolicyNo,TotalPolicy=COUNT(GED.PolicyNo),TotalSA=SUM(SumAssured),TotalPremium=SUM(GED.Premium),GED.PolicyType
INTO #GroupP
FROM tblGroupEndowmentDetails GED
INNER JOIN  tblGroupInformation GI 
ON GED.GroupId=GI.groupid 
WHERE GED.GroupId=ISNULL(@GroupId,GED.GroupId)
AND GED.DOC BETWEEN @FromDate AND @ToDate
AND PolicyStatus NOT IN('Cancel')
AND GED.PolicyType=ISNULL(@Status,GED.PolicyType)

GROUP BY GED.GroupId,GI.GroupName,GED.PolicyType,GED.PolicyNo
ORDER BY GroupId





SELECT * FROM #GroupP
--UNION ALL SELECT MAX(SN+1),'Total','',SUM(TotalPolicy),SUM(TotalSA),SUM(TotalPremium) FROM #GroupP
--ORDER BY SN

SELECT * FROM  #tempSearchPSummaryReport
DROP TABLE #GroupP

DROP TABLE #tempSearchPSummaryReport
RETURN



END


ELSE IF @Flag='GroupRPSummaryReport'
BEGIN

SELECT @GroupName=GroupName FROM tblGroupInformation WHERE GroupId=@GroupId
SELECT TOP 1 @FiscalYear=FiscalYear FROM tblgroupendowment WHERE GroupId=@GroupId
SELECT @user AS 'userID',CONVERT(VARCHAR(10),GETDATE(),105) AS 'GeneratedOn',@GroupName As [Group Name], @FiscalYear AS [Fiscal Year],
CONVERT(VARCHAR(10),@GroupId,105) AS [Group Code:],
CONVERT(VARCHAR(10),@FromDate,105) AS [Paid Date From:],
CONVERT(VARCHAR(10),@ToDate,105) AS [Paid Date To:]
INTO  #tempSearchRPSummaryReport

SELECT ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) AS SN, GED.GroupId,GroupName,TotalPolicy=COUNT(GED.PolicyNo),TotalSA=SUM(GE.SumAssured),TotalPremium=SUM(GED.Premium)
INTO #GroupRP
FROM tblGroupEndowmentTermPaid GED
INNER JOIN tblGroupEndowmentDetails GE
ON GED.PolicyNo=GE.PolicyNo  AND GE.RegisterNo=GED.RegisterNo
INNER join dbo.tblGroupEndowment id(nolock) on GE.RegisterNo=id.RegisterNo
INNER JOIN tblGroupInformation GI
ON GED.GroupId=GI.GroupId
INNER JOIN dbo.tblBranch AS TB2 (NOLOCK) ON TB2.Branch = GED.Branch
INNER JOIN dbo.vwAccountPostingV2 AS vapv(NOLOCK) ON vapv.VoucherNo = GED.VoucherNo
WHERE InstalmenType='R'
AND CAST(vapv.Valuedate AS DATE)  BETWEEN @FromDate AND @ToDate
AND GE.PolicyStatus NOT IN('Cancel')
AND GED.GroupId=ISNULL(@GroupId,GED.GroupId)
AND GED.Instalment <> '1'
AND vapv.Amount<0
AND vapv.Narration LIKE 'Renewal Group Endowment Income on%'
AND vapv.IsReverse is NULL
AND vapv.VoucherCode='RP'
GROUP BY GED.GroupId,GroupName


ALTER TABLE #GroupRP 
ALTER COLUMN GroupId VARCHAR(100)

ALTER TABLE #GroupRP
ALTER COLUMN TotalPolicy INT

SELECT * FROM #GroupRP
UNION ALL SELECT MAX(SN+1),'Total','',SUM(TotalPolicy),SUM(TotalSA),SUM(TotalPremium) FROM #GroupRP
ORDER BY GroupId

SELECT * FROM  #tempSearchRPSummaryReport
DROP TABLE #GroupRP
RETURN



END




END
GO
