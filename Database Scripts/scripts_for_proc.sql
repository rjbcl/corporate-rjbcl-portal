-- GROUP POLICY LOAN REPAYMENT

EXEC proc_copo_GroupReport
                    @flag = 'rptGroupPolicyLoanRepayment',
                    @user = 'report_reader',
                    @fromDate = '2019-04-06',
                    @toDate = '2026-04-06',
                    @PolicyNo = NULL,
                    @Status = NULL,
                    @groupId = '179';



--TRANSFER REPORT

EXEC proc_copo_GroupReport 
                    @flag='GroupTransferReport' ,
                    @User = 'report_reader_copo',
                    @TransferDateFrom= '04/13/2019',
                    @TransferDateTo = '04/13/2026',
                    @GroupId = '052';



--Maturity Forecasting Report
EXEC proc_copo_GroupReport 
                    @flag = 'MaturityForecastingReport',
                    @User = 'report_reader',
                    @GroupId = '052',
                    @FromDate = '04/13/2020',
                    @ToDate = '04/13/2026';


--LOAN REPAYMENT REPORT
EXEC proc_copo_groupReport
                    @flag = 'rptGroupPolicyLoanRepayment',
                    @user = 'report_reader',
                    @fromDate = '04/13/2020',
                    @toDate = '04/13/2026',
                    @PolicyNo = NULL,
                    @Status = NULL,
                    @groupId = '052';


--DEATH CLAIM REPORT
EXEC proc_copo_GroupReport 
                    @flag = 'GroupDeathReport',
                    @User = 'report_reader',
                    @GroupType = 'Group',
                    @DateOption = 'DeathPaid',
                    @FromDate = '04/13/2020',
                    @ToDate = '04/13/2026',
                    @DOCDateFrom = NULL,
                    @DOCDateTo = NULL,
                    @PolicyNo = NULL,
                    @GroupId = '052';


--MATURITY CLAIM REPORT
EXEC proc_copo_GroupReport 
                    @flag = 'GroupMaturityReport',
                    @User = 'report_reader',
                    @GroupType = 'Group',
                    @FromDate = '04/13/2020',
                    @ToDate = '04/13/2026',
                    @DOCDateFrom = NULL,
                    @DOCDateTo = NULL,
                    @PolicyNo = NULL,
                    @GroupId = '052';


--SURRENDER CLAIM REPORT
EXEC proc_copo_GroupReport 
                    @flag = 'GroupSurrenderReport',
                    @User = 'report_reader',
                    @GroupType = 'Group',
                    @FromDate = '04/13/2020',
                    @ToDate = '04/13/2026',
                    @DOCDateFrom = NULL,
                    @DOCDateTo = NULL,
                    @PolicyNo = NULL,
                    @GroupId = '052';



-- New Business filtered by ValueDate
EXEC proc_copo_BusinessDetail
    @GroupId  = '101',
    @FromDate = '2024-07-16',
    @ToDate   = '2025-07-16',
    @FilterBy = 'ValueDate',
    @Flag     = 'NB';

-- Renewal Business filtered by PaidDate
EXEC proc_copo_BusinessDetail
    @GroupId  = '101',
    @FromDate = '2024-07-16',
    @ToDate   = '2025-07-16',
    @FilterBy = 'PaidDate',
    @Flag     = 'RB';



--Dashboard Data
EXEC proc_copo_dashboard_data
    @groupids = '052,053';