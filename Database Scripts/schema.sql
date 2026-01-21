DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'account_type') THEN
        CREATE TYPE account_type AS ENUM ('company', 'individual', 'loan');
    END IF;
END$$;

CREATE TABLE IF NOT EXISTS account (
    username VARCHAR(100) PRIMARY KEY,
    password VARCHAR(100) NOT NULL,
    type account_type NOT NULL
);

CREATE TABLE IF NOT EXISTS company (
    company_id SERIAL PRIMARY KEY,
    username VARCHAR(100) NOT NULL,
    company_name VARCHAR(200) NOT NULL,
    CONSTRAINT fk_company_account
        FOREIGN KEY (username) REFERENCES account(username)
        ON DELETE CASCADE
);


CREATE TABLE groups (
    row_id SERIAL PRIMARY KEY,       
    company_id INTEGER NOT NULL,        
    group_id VARCHAR(20) UNIQUE,          
    group_name VARCHAR(200),              
    isdeleted BOOLEAN NOT NULL DEFAULT FALSE,
    isactive BOOLEAN NOT NULL DEFAULT TRUE,

    -- AuditBase fields
    created_by VARCHAR(30),
    modified_by VARCHAR(30),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_company
        FOREIGN KEY (company_id)
        REFERENCES company (company_id)       
        ON DELETE CASCADE
);



CREATE TABLE IF NOT EXISTS individual (
    user_id SERIAL PRIMARY KEY,          
    group_id INT NOT NULL,              
    username VARCHAR(100) NOT NULL,     
    user_full_name VARCHAR(200),             
    CONSTRAINT fk_individual_group
        FOREIGN KEY (group_id) 
        REFERENCES groups(group_id)
        ON DELETE CASCADE,
    CONSTRAINT fk_individual_account
        FOREIGN KEY (username) 
        REFERENCES account(username)
        ON DELETE CASCADE
);
USE [iSolutionLife_RBS_Migration_0840814]
GO

/****** Object:  Table [dbo].[tblGroupInformation]    Script Date: 1/14/2026 2:35:33 PM ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

CREATE TABLE [dbo].[tblGroupInformation](
	[RowId] [bigint] IDENTITY(1,1) NOT NULL,
	[GroupName] [varchar](50) NULL,
	[GroupNameNepali] [nvarchar](50) NULL,
	[DiscountRate] [money] NULL,
	[FiscalYear] [varchar](50) NULL,
	[ShortName] [varchar](50) NULL,
	[MasterPolicyNo] [varchar](50) NULL,
	[GroupId] [varchar](50) NULL,
	[CreatedBy] [varchar](50) NULL,
	[CreatedDate] [datetime] NULL,
	[IsActive] [bit] NULL,
	[GroupType] [varchar](100) NULL,
	[AccountNumber] [bigint] NULL,
	[PSeq] [varchar](50) NULL,
	[Gseq] [varchar](50) NULL,
	[ModifiedBy] [varchar](50) NULL,
	[ModifiedDate] [datetime] NULL,
	[RSeq] [int] NULL,
	[PlanID] [int] NULL,
	[ADBDiscountRate] [money] NULL,
	[RetirementAge] [int] NULL,
	[MinAge] [bigint] NULL,
	[MaxAge] [bigint] NULL,
	[MinTerm] [bigint] NULL,
	[MaxTerm] [bigint] NULL,
	[Rebate] [int] NULL,
	[P2Seq] [bigint] NULL,
	[DOC] [datetime] NULL,
	[G_LOAN] [varchar](10) NULL,
	[S_Policy] [varchar](50) NULL,
	[ADBAmount] [money] NULL,
	[ExtraPremium] [money] NULL,
	[Mode] [varchar](50) NULL,
	[Remarks] [varchar](50) NULL,
	[ADBRate] [money] NULL,
	[ExtraLoad] [money] NULL,
	[IsADB] [varchar](10) NULL,
 CONSTRAINT [tblGroupInformation_PK] PRIMARY KEY CLUSTERED 
(
	[RowId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO


CREATE TABLE audit_log (
    log_id SERIAL PRIMARY KEY,
    action VARCHAR(50) NOT NULL CHECK (
        action IN (
            'password_reset',
            'role_change',
            'soft_delete',
            'hard_delete',
            'create',
            'update'
        )
    ),
    target_username VARCHAR(100) NOT NULL,
    target_type VARCHAR(50) NOT NULL CHECK (
        target_type IN ('account', 'company', 'individual')
    ),
    performed_by VARCHAR(100) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    details TEXT
);


--Create tblGroupEndowmentDetails table
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE TABLE [dbo].[tblGroupEndowmentDetails](
	[RowId] [bigint] IDENTITY(1,1) NOT NULL,
	[PolicyNo] [varchar](50) NOT NULL,
	[RegisterNo] [varchar](50) NOT NULL,
	[Branch] [varchar](50) NOT NULL,
	[GroupId] [varchar](50) NOT NULL,
	[PaidDate] [datetime] NULL,
	[DOC] [date] NOT NULL,
	[Term] [smallint] NOT NULL,
	[SumAssured] [money] NOT NULL,
	[Premium] [money] NOT NULL,
	[FUP] [datetime] NOT NULL,
	[Instalment] [smallint] NULL,
	[PaidAmount] [money] NULL,
	[MaturityDate] [date] NOT NULL,
	[BatchNo] [varchar](50) NULL,
	[PostedBy] [varchar](50) NOT NULL,
	[Remarks] [varchar](50) NULL,
	[Intrest] [money] NULL,
	[LateFine] [money] NULL,
	[PolicyStatus] [varchar](10) NOT NULL,
	[PolicyType] [varchar](5) NULL,
	[ClaimStatus] [varchar](20) NULL,
	[LateFinePercent] [money] NULL,
	[CreatedBy] [varchar](50) NULL,
	[CreatedDate] [datetime] NULL,
	[ReducedInstalment] [int] NULL,
PRIMARY KEY CLUSTERED 
(
	[RowId] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY],
UNIQUE NONCLUSTERED 
(
	[RegisterNo] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO
CREATE NONCLUSTERED INDEX [tblGroupEndowmentDetails_DOC] ON [dbo].[tblGroupEndowmentDetails]
(
	[DOC] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
CREATE NONCLUSTERED INDEX [tblGroupEndowmentDetails_FUP] ON [dbo].[tblGroupEndowmentDetails]
(
	[FUP] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, SORT_IN_TEMPDB = OFF, DROP_EXISTING = OFF, ONLINE = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
GO
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO
CREATE   TRIGGER [dbo].[tr_tblGroupEndowmentDetails_AuditLog]
ON [dbo].[tblGroupEndowmentDetails]
AFTER UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    INSERT INTO tblCustomAuditLog (TableName, Operation, RecordID, PolicyNo, OldData, NewData, ClientIP)
    SELECT 
        'tblGroupEndowmentDetails',
        CASE WHEN i.rowid IS NOT NULL THEN 'UPDATE' ELSE 'DELETE' END,
        CAST(d.rowid AS NVARCHAR),
        d.PolicyNo,
        (SELECT d.* FOR JSON PATH, WITHOUT_ARRAY_WRAPPER),
        CASE 
            WHEN i.rowid IS NOT NULL THEN (SELECT i.* FOR JSON PATH, WITHOUT_ARRAY_WRAPPER)
            ELSE '{}' 
    END
        
    ,ClientIP = dbo.GetClientIP() FROM deleted d
    LEFT JOIN inserted i ON d.rowid = i.rowid;
END   
GO
ALTER TABLE [dbo].[tblGroupEndowmentDetails] ENABLE TRIGGER [tr_tblGroupEndowmentDetails_AuditLog]
GO







SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public';


Select * from company;
Select * from groups;
Select * from account;
Select * from account_groups;
select * from individual;
select * from policy;
select * from audit_log;
