from rest_framework import viewsets, filters, status  # type: ignore
from rest_framework.permissions import IsAuthenticated  # type: ignore
from rest_framework.decorators import action, api_view, permission_classes, authentication_classes  # type: ignore
from rest_framework.response import Response  # type: ignore
from rest_framework.authentication import SessionAuthentication  # type: ignore 
import django_filters  # type: ignore

from django.db import connections  # type: ignore

from main_system.models import Group as PortalGroup
from main_system.models import ReportAccessLog
from .authentication import APIKeyAuthentication
from .models import GroupEndowment, GroupInformation
from .serializers import GroupEndowmentSerializer, GroupInformationSerializer
from .permissions import IsCompanyUser
from .utils import log_report_access


# Shorthand — every API view uses these two authenticators
_AUTH = [APIKeyAuthentication, SessionAuthentication]


# ============================================================
# REPORT HELPERS
# ============================================================

def _serialize_row(columns, row):
    """Convert a DB row tuple into a dict, handling types consistently."""
    row_dict = {}
    for i, value in enumerate(row):
        col_name = columns[i]
        if value is None:
            row_dict[col_name] = None
        elif hasattr(value, 'isoformat'):
            row_dict[col_name] = value.isoformat()
        elif isinstance(value, (int, float)):
            row_dict[col_name] = value
        else:
            row_dict[col_name] = str(value)
    return row_dict


def _fetch_all_resultsets(cursor):
    """Iterate through all result sets from a cursor, collecting all rows."""
    results = []
    while True:
        if cursor.description:
            columns = [col[0] for col in cursor.description]
            for row in cursor.fetchall():
                results.append(_serialize_row(columns, row))
        if not cursor.nextset():
            break
    return results


def _verify_group_access(request, group_id):
    """
    Verify the requesting company user owns the given group.
    Returns (True, None) on success or (False, Response) on failure.
    """
    if request.user.is_superuser or request.user.is_staff:
        return True, None

    company = request.user.company_profile.company
    exists = PortalGroup.objects.filter(
        company=company,
        group_id=group_id,
        isdeleted=False,
    ).exists()

    if not exists:
        return False, Response(
            {'error': 'You can only access your own company groups'},
            status=403,
        )

    return True, None


# ============================================================
# REPORT VIEWS
# ============================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def maturity_forecasting_report(request):
    """POST /api/corporate/reports/maturity-forecasting/"""
    group_id  = request.data.get('group_id')
    from_date = request.data.get('from_date')
    to_date   = request.data.get('to_date')
    date_type = request.data.get('date_type', 'ad')

    if not all([group_id, from_date, to_date]):
        log_report_access(request=request, report_type='Maturity Forecasting Report',
                          sql_template='', params=[], status=ReportAccessLog.Status.INVALID_INPUT)
        return Response({'error': 'group_id, from_date, and to_date are required'}, status=400)

    allowed, error_response = _verify_group_access(request, group_id)
    if not allowed:
        log_report_access(request=request, report_type='Maturity Forecasting Report',
                          sql_template='', params=[], status=ReportAccessLog.Status.FORBIDDEN)
        return error_response

    sql = """
        SET NOCOUNT ON;
        EXEC proc_copo_GroupReport
            @flag = 'MaturityForecastingReport',
            @User = 'report_reader',
            @GroupId = %s,
            @FromDate = %s,
            @ToDate = %s;
    """
    try:
        with connections['company_external'].cursor() as cursor:
            cursor.execute(sql, [group_id, from_date, to_date])
            results = _fetch_all_resultsets(cursor)

        status_val = ReportAccessLog.Status.NO_DATA if not results else ReportAccessLog.Status.SUCCESS
        log_report_access(request=request, report_type='Maturity Forecasting Report',
                          sql_template=sql, params=[group_id, from_date, to_date], status=status_val)

        return Response({
            'success': True, 'count': len(results),
            'group_id': group_id, 'from_date': from_date,
            'to_date': to_date, 'date_type': date_type,
            'policies': results,
        })

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(request=request, report_type='Maturity Forecasting Report',
                          sql_template=sql, params=[group_id, from_date, to_date],
                          status=ReportAccessLog.Status.ERROR, exc=e)
        return Response({
            'error': f'Failed to generate report: {str(e)}',
            'details': error_details if request.user.is_superuser else None,
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def group_transfer_report(request):
    """POST /api/corporate/reports/group-transfer/"""
    group_id           = request.data.get('group_id')
    transfer_date_from = request.data.get('transfer_date_from')
    transfer_date_to   = request.data.get('transfer_date_to')
    date_type          = request.data.get('date_type', 'ad')

    if not all([group_id, transfer_date_from, transfer_date_to]):
        log_report_access(request=request, report_type='Group Transfer Report',
                          sql_template='', params=[], status=ReportAccessLog.Status.INVALID_INPUT)
        return Response(
            {'error': 'group_id, transfer_date_from, and transfer_date_to are required'},
            status=400,
        )

    allowed, error_response = _verify_group_access(request, group_id)
    if not allowed:
        log_report_access(request=request, report_type='Group Transfer Report',
                          sql_template='', params=[], status=ReportAccessLog.Status.FORBIDDEN)
        return error_response

    sql = """
        SET NOCOUNT ON;
        EXEC proc_copo_GroupReport
            @flag = 'GroupTransferReport',
            @User = 'report_reader_copo',
            @GroupId = %s,
            @TransferDateFrom = %s,
            @TransferDateTo = %s;
    """
    try:
        with connections['company_external'].cursor() as cursor:
            cursor.execute(sql, [group_id, transfer_date_from, transfer_date_to])
            results = _fetch_all_resultsets(cursor)

        status_val = ReportAccessLog.Status.NO_DATA if not results else ReportAccessLog.Status.SUCCESS
        log_report_access(request=request, report_type='Group Transfer Report',
                          sql_template=sql,
                          params=[group_id, transfer_date_from, transfer_date_to],
                          status=status_val)

        return Response({
            'success': True, 'count': len(results),
            'group_id': group_id,
            'transfer_date_from': transfer_date_from,
            'transfer_date_to': transfer_date_to,
            'date_type': date_type,
            'transfers': results,
        })

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(request=request, report_type='Group Transfer Report',
                          sql_template=sql,
                          params=[group_id, transfer_date_from, transfer_date_to],
                          status=ReportAccessLog.Status.ERROR, exc=e)
        return Response({
            'error': f'Failed to generate report: {str(e)}',
            'details': error_details if request.user.is_superuser else None,
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def loan_repayment_report(request):
    """POST /api/corporate/reports/loan-repayment/"""
    group_id  = request.data.get('group_id')
    from_date = request.data.get('from_date')
    to_date   = request.data.get('to_date')
    date_type = request.data.get('date_type', 'ad')

    if not all([group_id, from_date, to_date]):
        log_report_access(request=request, report_type='Loan Repayment Report',
                          sql_template='', params=[], status=ReportAccessLog.Status.INVALID_INPUT)
        return Response({'error': 'group_id, from_date, and to_date are required'}, status=400)

    allowed, error_response = _verify_group_access(request, group_id)
    if not allowed:
        log_report_access(request=request, report_type='Loan Repayment Report',
                          sql_template='', params=[], status=ReportAccessLog.Status.FORBIDDEN)
        return error_response

    sql = """
        SET NOCOUNT ON;
        EXEC proc_copo_groupReport
            @flag = 'rptGroupPolicyLoanRepayment',
            @user = 'report_reader',
            @fromDate = %s,
            @toDate = %s,
            @PolicyNo = NULL,
            @Status = NULL,
            @groupId = %s;
    """
    try:
        with connections['company_external'].cursor() as cursor:
            cursor.execute(sql, [from_date, to_date, group_id])
            results = _fetch_all_resultsets(cursor)

        status_val = ReportAccessLog.Status.NO_DATA if not results else ReportAccessLog.Status.SUCCESS
        log_report_access(request=request, report_type='Loan Repayment Report',
                          sql_template=sql, params=[from_date, to_date, group_id],
                          status=status_val)

        return Response({
            'success': True, 'count': len(results),
            'group_id': group_id, 'from_date': from_date,
            'to_date': to_date, 'date_type': date_type,
            'repayments': results,
        })

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(request=request, report_type='Loan Repayment Report',
                          sql_template=sql, params=[from_date, to_date, group_id],
                          status=ReportAccessLog.Status.ERROR, exc=e)
        return Response({
            'error': f'Failed to generate report: {str(e)}',
            'details': error_details if request.user.is_superuser else None,
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def policy_detail(request):
    """POST /api/corporate/policy-detail/"""
    policy_no = request.data.get('policy_no')

    if not policy_no:
        log_report_access(request=request, report_type='Policy Detail',
                          sql_template='', params=[],
                          status=ReportAccessLog.Status.INVALID_INPUT)
        return Response({'error': 'policy_no is required'}, status=400)

    # ── Resolve group_ids (identical pattern to policy_loans) ──────────────
    group_ids = request.session.get('company_group_ids')

    if not group_ids:
        if request.user.is_superuser or request.user.is_staff:
            group_ids = list(PortalGroup.objects.filter(
                isdeleted=False
            ).values_list('group_id', flat=True))
        else:
            try:
                company = request.user.company_profile.company
                if not company.isactive:
                    log_report_access(request=request, report_type='Policy Detail',
                                      sql_template='', params=[],
                                      status=ReportAccessLog.Status.FORBIDDEN)
                    return Response({'error': 'Company account is inactive'}, status=403)
                group_ids = list(PortalGroup.objects.filter(
                    company=company, isdeleted=False
                ).values_list('group_id', flat=True))
            except AttributeError:
                log_report_access(request=request, report_type='Policy Detail',
                                  sql_template='', params=[],
                                  status=ReportAccessLog.Status.FORBIDDEN)
                return Response({'error': 'User is not associated with a company'}, status=403)

        if not group_ids:
            log_report_access(request=request, report_type='Policy Detail',
                              sql_template='', params=[],
                              status=ReportAccessLog.Status.FORBIDDEN)
            return Response({'error': 'No groups found for your company'}, status=403)

        request.session['company_group_ids'] = group_ids

    # ── Queries ────────────────────────────────────────────────────────────
    verify_sql  = ''
    summary_sql = ''
    loan_sql    = ''
    params      = []

    try:
        with connections['company_external'].cursor() as cursor:
            placeholders = ','.join(['%s'] * len(group_ids))

            # 1. Access check
            verify_sql = f"""
                SELECT COUNT(1) FROM tblGroupEndowment
                WHERE policyNo = %s AND groupId IN ({placeholders})
            """
            cursor.execute(verify_sql, [policy_no] + group_ids)
            if cursor.fetchone()[0] == 0:
                log_report_access(request=request, report_type='Policy Detail',
                                  sql_template=verify_sql,
                                  params=[policy_no] + group_ids,
                                  status=ReportAccessLog.Status.FORBIDDEN)
                return Response({'error': 'Policy not found or access denied'}, status=403)

            # 2. Policy summary
            summary_sql = f"""
                SELECT * FROM view_copo_policySummary
                WHERE PolicyNo = %s AND GroupId IN ({placeholders})
            """
            params = [policy_no] + group_ids
            cursor.execute(summary_sql, params)
            summary_rows = []
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    summary_rows.append(_serialize_row(columns, row))

            # 3. Loan details
            loan_sql = """
                SELECT PolicyNo, loanID, LoanDate, LoanAmount, InterestRate,
                       Instalment, Status, LastPaidDate, VoucherNo
                FROM tblGroupPolicyLoanDetail
                WHERE policyNo = %s
            """
            cursor.execute(loan_sql, [policy_no])
            loan_rows = []
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    loan_rows.append(_serialize_row(columns, row))

        status_val = (
            ReportAccessLog.Status.NO_DATA
            if not summary_rows and not loan_rows
            else ReportAccessLog.Status.SUCCESS
        )
        log_report_access(request=request, report_type='Policy Detail',
                          sql_template=summary_sql, params=params,
                          status=status_val)

        return Response({
            'success': True,
            'policy_no': policy_no,
            'summary': summary_rows,
            'loans': loan_rows,
        }, status=200)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(request=request, report_type='Policy Detail',
                          sql_template=summary_sql or verify_sql,
                          params=params,
                          status=ReportAccessLog.Status.ERROR, exc=e)
        return Response({
            'error': f'Failed to fetch policy detail: {str(e)}',
            'details': error_details if request.user.is_superuser else None,
        }, status=500)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def death_claim_report(request):
    """POST /api/corporate/reports/death-claim/"""
    group_id  = request.data.get('group_id')
    from_date = request.data.get('from_date')
    to_date   = request.data.get('to_date')

    if not all([group_id, from_date, to_date]):
        log_report_access(request=request, report_type='Death Claim Report',
                          sql_template='', params=[], status=ReportAccessLog.Status.INVALID_INPUT)
        return Response({'error': 'group_id, from_date, and to_date are required'}, status=400)

    allowed, error_response = _verify_group_access(request, group_id)
    if not allowed:
        log_report_access(request=request, report_type='Death Claim Report',
                          sql_template='', params=[], status=ReportAccessLog.Status.FORBIDDEN)
        return error_response

    sql = """
        SET NOCOUNT ON;
        EXEC proc_copo_GroupReport
            @flag = 'GroupDeathReport',
            @User = 'report_reader',
            @GroupType = 'Group',
            @DateOption = 'DeathPaid',
            @FromDate = %s,
            @ToDate = %s,
            @DOCDateFrom = NULL,
            @DOCDateTo = NULL,
            @PolicyNo = NULL,
            @GroupId = %s;
    """
    try:
        with connections['company_external'].cursor() as cursor:
            cursor.execute(sql, [from_date, to_date, group_id])
            results = _fetch_all_resultsets(cursor)

        status_val = ReportAccessLog.Status.NO_DATA if not results else ReportAccessLog.Status.SUCCESS
        log_report_access(request=request, report_type='Death Claim Report',
                          sql_template=sql, params=[from_date, to_date, group_id],
                          status=status_val)
        return Response(results)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(request=request, report_type='Death Claim Report',
                          sql_template=sql, params=[from_date, to_date, group_id],
                          status=ReportAccessLog.Status.ERROR, exc=e)
        return Response({
            'error': f'Failed to generate death claim report: {str(e)}',
            'details': error_details if request.user.is_superuser else None,
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def maturity_claim_report(request):
    """POST /api/corporate/reports/maturity-claim/"""
    group_id  = request.data.get('group_id')
    from_date = request.data.get('from_date')
    to_date   = request.data.get('to_date')

    if not all([group_id, from_date, to_date]):
        log_report_access(request=request, report_type='Maturity Claim Report',
                          sql_template='', params=[], status=ReportAccessLog.Status.INVALID_INPUT)
        return Response({'error': 'group_id, from_date, and to_date are required'}, status=400)

    allowed, error_response = _verify_group_access(request, group_id)
    if not allowed:
        log_report_access(request=request, report_type='Maturity Claim Report',
                          sql_template='', params=[], status=ReportAccessLog.Status.FORBIDDEN)
        return error_response

    sql = """
        SET NOCOUNT ON;
        EXEC proc_copo_GroupReport
            @flag = 'GroupMaturityReport',
            @User = 'report_reader',
            @GroupType = 'Group',
            @FromDate = %s,
            @ToDate = %s,
            @DOCDateFrom = NULL,
            @DOCDateTo = NULL,
            @PolicyNo = NULL,
            @GroupId = %s;
    """
    try:
        with connections['company_external'].cursor() as cursor:
            cursor.execute(sql, [from_date, to_date, group_id])
            results = _fetch_all_resultsets(cursor)

        status_val = ReportAccessLog.Status.NO_DATA if not results else ReportAccessLog.Status.SUCCESS
        log_report_access(request=request, report_type='Maturity Claim Report',
                          sql_template=sql, params=[from_date, to_date, group_id],
                          status=status_val)
        return Response(results)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(request=request, report_type='Maturity Claim Report',
                          sql_template=sql, params=[from_date, to_date, group_id],
                          status=ReportAccessLog.Status.ERROR, exc=e)
        return Response({
            'error': f'Failed to generate maturity claim report: {str(e)}',
            'details': error_details if request.user.is_superuser else None,
        }, status=500)


VALID_FLAGS     = {'NB', 'RB'}
VALID_FILTER_BY = {'PaidDate', 'ValueDate'}


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def group_business_detail_report(request):
    """POST /api/corporate/reports/group-business-detail/"""
    group_id  = request.data.get('group_id')
    flag      = request.data.get('flag')
    filter_by = request.data.get('filter_by')
    from_date = request.data.get('from_date')
    to_date   = request.data.get('to_date')

    report_name = (
        'New Business Detail Report' if flag == 'NB'
        else 'Renewal Business Detail Report'
    )

    missing = [
        f for f, v in {
            'group_id': group_id, 'flag': flag, 'filter_by': filter_by,
            'from_date': from_date, 'to_date': to_date,
        }.items() if not v
    ]
    if missing:
        log_report_access(request=request, report_type=report_name,
                          sql_template='', params=[], status=ReportAccessLog.Status.INVALID_INPUT)
        return Response({'error': f'Missing required fields: {", ".join(missing)}'}, status=400)

    if flag not in VALID_FLAGS:
        log_report_access(request=request, report_type='Business Detail Report',
                          sql_template='', params=[], status=ReportAccessLog.Status.INVALID_INPUT)
        return Response(
            {'error': f'Invalid flag "{flag}". Must be one of: {", ".join(VALID_FLAGS)}'},
            status=400,
        )

    if filter_by not in VALID_FILTER_BY:
        log_report_access(request=request, report_type=report_name,
                          sql_template='', params=[], status=ReportAccessLog.Status.INVALID_INPUT)
        return Response(
            {'error': f'Invalid filter_by "{filter_by}". Must be one of: {", ".join(VALID_FILTER_BY)}'},
            status=400,
        )

    allowed, error_response = _verify_group_access(request, group_id)
    if not allowed:
        log_report_access(request=request, report_type=report_name,
                          sql_template='', params=[], status=ReportAccessLog.Status.FORBIDDEN)
        return error_response

    sql = """
        SET NOCOUNT ON;
        EXEC proc_copo_BusinessDetail
            @GroupId  = %s,
            @FromDate = %s,
            @ToDate   = %s,
            @FilterBy = %s,
            @Flag     = %s;
    """
    try:
        with connections['company_external'].cursor() as cursor:
            cursor.execute(sql, [group_id, from_date, to_date, filter_by, flag])
            results = _fetch_all_resultsets(cursor)

        status_val = ReportAccessLog.Status.NO_DATA if not results else ReportAccessLog.Status.SUCCESS
        log_report_access(request=request, report_type=report_name,
                          sql_template=sql,
                          params=[group_id, from_date, to_date, filter_by, flag],
                          status=status_val)
        return Response(results)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(request=request, report_type=report_name,
                          sql_template=sql,
                          params=[group_id, from_date, to_date, filter_by, flag],
                          status=ReportAccessLog.Status.ERROR, exc=e)
        return Response({
            'error': f'Failed to generate group business detail report: {str(e)}',
            'details': error_details if request.user.is_superuser else None,
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def surrender_claim_report(request):
    """POST /api/corporate/reports/surrender-claim/"""
    group_id  = request.data.get('group_id')
    from_date = request.data.get('from_date')
    to_date   = request.data.get('to_date')

    if not all([group_id, from_date, to_date]):
        log_report_access(request=request, report_type='Surrender Claim Report',
                          sql_template='', params=[], status=ReportAccessLog.Status.INVALID_INPUT)
        return Response({'error': 'group_id, from_date, and to_date are required'}, status=400)

    allowed, error_response = _verify_group_access(request, group_id)
    if not allowed:
        log_report_access(request=request, report_type='Surrender Claim Report',
                          sql_template='', params=[], status=ReportAccessLog.Status.FORBIDDEN)
        return error_response

    sql = """
        SET NOCOUNT ON;
        EXEC proc_copo_GroupReport
            @flag = 'GroupSurrenderReport',
            @User = 'report_reader',
            @GroupType = 'Group',
            @FromDate = %s,
            @ToDate = %s,
            @DOCDateFrom = NULL,
            @DOCDateTo = NULL,
            @PolicyNo = NULL,
            @GroupId = %s;
    """
    try:
        with connections['company_external'].cursor() as cursor:
            cursor.execute(sql, [from_date, to_date, group_id])
            results = _fetch_all_resultsets(cursor)

        status_val = ReportAccessLog.Status.NO_DATA if not results else ReportAccessLog.Status.SUCCESS
        log_report_access(request=request, report_type='Surrender Claim Report',
                          sql_template=sql, params=[from_date, to_date, group_id],
                          status=status_val)
        return Response(results)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(request=request, report_type='Surrender Claim Report',
                          sql_template=sql, params=[from_date, to_date, group_id],
                          status=ReportAccessLog.Status.ERROR, exc=e)
        return Response({
            'error': f'Failed to generate surrender claim report: {str(e)}',
            'details': error_details if request.user.is_superuser else None,
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def policy_summary_report(request):
    """POST /api/corporate/reports/policy-summary/"""
    policy_no = request.data.get('policy_no')

    if not policy_no:
        log_report_access(request=request, report_type='Policy Summary Report',
                          sql_template='', params=[], status=ReportAccessLog.Status.INVALID_INPUT)
        return Response({'error': 'policy_no is required'}, status=400)

    if request.user.is_superuser or request.user.is_staff:
        group_ids = list(PortalGroup.objects.filter(
            isdeleted=False
        ).values_list('group_id', flat=True))
    else:
        company = request.user.company_profile.company

        if not company.isactive:
            log_report_access(request=request, report_type='Policy Summary Report',
                              sql_template='', params=[], status=ReportAccessLog.Status.FORBIDDEN)
            return Response({'error': 'Company account is inactive'}, status=403)

        group_ids = list(PortalGroup.objects.filter(
            company=company, isdeleted=False
        ).values_list('group_id', flat=True))

        if not group_ids:
            log_report_access(request=request, report_type='Policy Summary Report',
                              sql_template='', params=[], status=ReportAccessLog.Status.FORBIDDEN)
            return Response({'error': 'No groups found for your company'}, status=404)

    sql = ''
    params = []
    try:
        with connections['company_external'].cursor() as cursor:
            placeholders = ','.join(['%s'] * len(group_ids))
            sql = f"""
                SELECT * FROM view_copo_policySummary
                WHERE PolicyNo = %s AND GroupId IN ({placeholders})
            """
            params = [policy_no] + group_ids
            cursor.execute(sql, params)

            results = []
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    results.append(_serialize_row(columns, row))

        status_val = ReportAccessLog.Status.NO_DATA if not results else ReportAccessLog.Status.SUCCESS
        log_report_access(request=request, report_type='Policy Summary Report',
                          sql_template=sql, params=params, status=status_val)
        return Response(results)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(request=request, report_type='Policy Summary Report',
                          sql_template=sql, params=params,
                          status=ReportAccessLog.Status.ERROR, exc=e)
        return Response({
            'error': f'Failed to generate report: {str(e)}',
            'details': error_details if request.user.is_superuser else None,
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def surrender_calculator(request):
    """POST /api/corporate/surrender-calculator/"""
    policy_no  = request.data.get('policy_no')
    claim_date = request.data.get('claim_date')

    if not policy_no:
        log_report_access(request=request, report_type='Surrender Calculator',
                          sql_template='', params=[], status=ReportAccessLog.Status.INVALID_INPUT)
        return Response({'error': 'policy_no is required'}, status=400)

    if request.user.is_superuser or request.user.is_staff:
        group_ids = list(PortalGroup.objects.filter(
            isdeleted=False
        ).values_list('group_id', flat=True))
    else:
        company = request.user.company_profile.company

        if not company.isactive:
            log_report_access(request=request, report_type='Surrender Calculator',
                              sql_template='', params=[], status=ReportAccessLog.Status.FORBIDDEN)
            return Response({'error': 'Company account is inactive'}, status=403)

        group_ids = list(PortalGroup.objects.filter(
            company=company, isdeleted=False
        ).values_list('group_id', flat=True))

        if not group_ids:
            log_report_access(request=request, report_type='Surrender Calculator',
                              sql_template='', params=[], status=ReportAccessLog.Status.FORBIDDEN)
            return Response({'error': 'No groups found for your company'}, status=404)

    sql = ''
    params = []
    try:
        with connections['company_external'].cursor() as cursor:
            if claim_date:
                sql = "EXEC proc_copo_surrender_calculator @PolicyNo = %s, @ClaimDate = %s"
                params = [policy_no, claim_date]
            else:
                sql = "EXEC proc_copo_surrender_calculator @PolicyNo = %s"
                params = [policy_no]

            cursor.execute(sql, params)

            row = cursor.fetchone()
            if not row:
                log_report_access(request=request, report_type='Surrender Calculator',
                                  sql_template=sql, params=params,
                                  status=ReportAccessLog.Status.NO_DATA)
                return Response({'error': 'Policy not found or access denied'}, status=404)

            columns = [col[0] for col in cursor.description]
            result = _serialize_row(columns, row)

        log_report_access(request=request, report_type='Surrender Calculator',
                          sql_template=sql, params=params,
                          status=ReportAccessLog.Status.SUCCESS)
        return Response(result)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(request=request, report_type='Surrender Calculator',
                          sql_template=sql, params=params,
                          status=ReportAccessLog.Status.ERROR, exc=e)
        return Response({
            'error': f'Failed to retrieve surrender data: {str(e)}',
            'details': error_details if request.user.is_superuser else None,
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def policy_search(request):
    """POST /api/corporate/reports/policy-search/"""
    query = request.data.get('q', '').strip()

    if not query:
        return Response([], status=200)

    group_ids = request.session.get('company_group_ids')

    if not group_ids:
        if request.user.is_superuser or request.user.is_staff:
            group_ids = list(PortalGroup.objects.filter(
                isdeleted=False
            ).values_list('group_id', flat=True))
        else:
            try:
                company = request.user.company_profile.company
                if not company.isactive:
                    return Response({'error': 'Company account is inactive'}, status=403)
                group_ids = list(PortalGroup.objects.filter(
                    company=company, isdeleted=False
                ).values_list('group_id', flat=True))
            except AttributeError:
                return Response({'error': 'User is not associated with a company'}, status=403)

        if not group_ids:
            return Response([], status=200)

        request.session['company_group_ids'] = group_ids

    try:
        with connections['company_external'].cursor() as cursor:
            placeholders = ','.join(['%s'] * len(group_ids))
            sql = f"""
                SELECT DISTINCT TOP 15 policyNo, name, employeeid
                FROM tblGroupEndowment
                WHERE groupId IN ({placeholders})
                AND (ISNULL(policyNo, '') + ' ' + ISNULL(name, '') + ' ' + ISNULL(employeeid, '')) LIKE %s
            """
            cursor.execute(sql, group_ids + [f'%{query}%'])
            rows = cursor.fetchall()

        return Response(
            [{'policyNo': r[0], 'name': r[1], 'employeeid': r[2]} for r in rows],
            status=200,
        )

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return Response({
            'error': f'Search failed: {str(e)}',
            'details': error_details if request.user.is_superuser else None,
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def policy_loans(request):
    """POST /api/corporate/reports/policy-loans/"""
    policy_no = request.data.get('policy_no')

    if not policy_no:
        log_report_access(request=request, report_type='Policy Loans Report',
                          sql_template='', params=[], status=ReportAccessLog.Status.INVALID_INPUT)
        return Response({'error': 'policy_no is required'}, status=400)

    group_ids = request.session.get('company_group_ids')

    if not group_ids:
        if request.user.is_superuser or request.user.is_staff:
            group_ids = list(PortalGroup.objects.filter(
                isdeleted=False
            ).values_list('group_id', flat=True))
        else:
            try:
                company = request.user.company_profile.company
                if not company.isactive:
                    log_report_access(request=request, report_type='Policy Loans Report',
                                      sql_template='', params=[],
                                      status=ReportAccessLog.Status.FORBIDDEN)
                    return Response({'error': 'Company account is inactive'}, status=403)
                group_ids = list(PortalGroup.objects.filter(
                    company=company, isdeleted=False
                ).values_list('group_id', flat=True))
            except AttributeError:
                log_report_access(request=request, report_type='Policy Loans Report',
                                  sql_template='', params=[],
                                  status=ReportAccessLog.Status.FORBIDDEN)
                return Response({'error': 'User is not associated with a company'}, status=403)

        if not group_ids:
            return Response([], status=200)

        request.session['company_group_ids'] = group_ids

    try:
        with connections['company_external'].cursor() as cursor:
            placeholders = ','.join(['%s'] * len(group_ids))
            verify_sql = f"""
                SELECT COUNT(1) FROM tblGroupEndowment
                WHERE policyNo = %s AND groupId IN ({placeholders})
            """
            cursor.execute(verify_sql, [policy_no] + group_ids)
            if cursor.fetchone()[0] == 0:
                log_report_access(request=request, report_type='Policy Loans Report',
                                  sql_template=verify_sql, params=[policy_no] + group_ids,
                                  status=ReportAccessLog.Status.FORBIDDEN)
                return Response({'error': 'Policy not found or access denied'}, status=403)

            loan_sql = """
                SELECT PolicyNo, loanID, LoanDate, LoanAmount, InterestRate,
                       Instalment, Status, LastPaidDate, VoucherNo
                FROM tblGroupPolicyLoanDetail
                WHERE policyNo = %s
            """
            cursor.execute(loan_sql, [policy_no])

            results = []
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                for row in cursor.fetchall():
                    results.append(_serialize_row(columns, row))

        status_val = ReportAccessLog.Status.NO_DATA if not results else ReportAccessLog.Status.SUCCESS
        log_report_access(request=request, report_type='Policy Loans Report',
                          sql_template=loan_sql, params=[policy_no], status=status_val)
        return Response(results, status=200)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(request=request, report_type='Policy Loans Report',
                          sql_template='', params=[],
                          status=ReportAccessLog.Status.ERROR, exc=e)
        return Response({
            'error': f'Failed to fetch loan details: {str(e)}',
            'details': error_details if request.user.is_superuser else None,
        }, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def company_policies_web(request):
    """GET /api/corporate/endowments/by_company/?company_id=<id>"""
    company_id = request.query_params.get('company_id')

    if not company_id:
        return Response({'error': 'company_id parameter is required'}, status=400)

    try:
        company_id = int(company_id)
    except ValueError:
        return Response({'error': 'company_id must be a valid integer'}, status=400)

    if not request.user.is_superuser and not request.user.is_staff:
        user_company_id = request.user.company_profile.company.company_id
        if user_company_id != company_id:
            return Response({'error': 'You can only access your own company data'}, status=403)

    portal_groups = PortalGroup.objects.filter(
        company__company_id=company_id,
        isdeleted=False,
    )
    group_ids = list(portal_groups.values_list('group_id', flat=True))

    if not group_ids:
        return Response({
            'company_id': company_id,
            'group_ids': [],
            'summary': {},
            'latest_policies': [],
            'fup_data': [],
            'message': 'No groups found for this company',
        })

    group_ids_csv = ','.join(str(g) for g in group_ids)

    with connections['company_external'].cursor() as cursor:
        cursor.execute("EXEC proc_copo_dashboard_data @groupids = %s", [group_ids_csv])

        latest_policies = [
            dict(zip([col[0] for col in cursor.description], row))
            for row in cursor.fetchall()
        ]
        cursor.nextset()
        summary = dict(zip([col[0] for col in cursor.description], cursor.fetchone()))
        cursor.nextset()
        fup_data = [
            dict(zip([col[0] for col in cursor.description], row))
            for row in cursor.fetchall()
        ]

    return Response({
        'company_id': company_id,
        'group_ids': group_ids,
        'summary': summary,
        'latest_policies': latest_policies,
        'fup_data': fup_data,
    })


# ============================================================
# VIEWSETS
# ============================================================

class CompanyPoliciesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API endpoint for company users to access their policies.
    """
    serializer_class = GroupEndowmentSerializer
    permission_classes = [IsAuthenticated, IsCompanyUser]
    authentication_classes = _AUTH

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['policy_status', 'fiscal_year', 'gender', 'policy_type',
                        'is_adb', 'employee_id', 'claim_status']
    search_fields = ['name', 'nep_name', 'policy_no', 'employee_id', 'mobile', 'email']
    ordering_fields = ['maturity_date', 'doc', 'name', 'premium', 'sum_assured']
    ordering = ['-maturity_date']

    def get_queryset(self):
        company = self.request.user.company_profile.company
        group_ids = list(PortalGroup.objects.filter(
            company=company, isdeleted=False
        ).values_list('group_id', flat=True))
        return GroupEndowment.objects.using('company_external').filter(
            group_id__in=group_ids
        )

    @action(detail=False, methods=['POST'])
    def statistics(self, request):
        """POST /api/company/policies/statistics/"""
        queryset = self.get_queryset()
        total = queryset.count()
        active = queryset.filter(policy_status='A').count()
        lapsed = queryset.filter(policy_status='L').count()
        total_sa = sum(float(p.sum_assured or 0) for p in queryset)
        total_premium = sum(float(p.premium or 0) for p in queryset)

        return Response({
            'total_policies': total,
            'active_policies': active,
            'lapsed_policies': lapsed,
            'inactive_policies': total - active - lapsed,
            'total_sum_assured': total_sa,
            'total_premium': total_premium,
        })


class GroupInformationFilter(django_filters.FilterSet):
    group_id = django_filters.BaseInFilter(field_name='group_id', lookup_expr='in')

    class Meta:
        model = GroupInformation
        fields = {
            'is_active': ['exact'],
            'group_name': ['icontains'],
        }


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def group_information(request):
    """GET /api/corporate/groups/"""
    user = request.user

    if user.is_superuser or user.is_staff:
        company_id = request.query_params.get('company_id')
        if company_id:
            try:
                company_id = int(company_id)
                group_ids = list(PortalGroup.objects.filter(
                    company__company_id=company_id, isdeleted=False
                ).values_list('group_id', flat=True))
            except (ValueError, TypeError):
                log_report_access(request=request, report_type='Group Information',
                                  sql_template='', params=[],
                                  status=ReportAccessLog.Status.INVALID_INPUT)
                return Response({'error': 'Invalid company_id'}, status=400)
        else:
            group_ids = list(PortalGroup.objects.filter(
                isdeleted=False
            ).values_list('group_id', flat=True))
    else:
        try:
            company = user.company_profile.company
            if not company.isactive:
                log_report_access(request=request, report_type='Group Information',
                                  sql_template='', params=[],
                                  status=ReportAccessLog.Status.FORBIDDEN)
                return Response({'error': 'Company account is inactive'}, status=403)
            group_ids = list(PortalGroup.objects.filter(
                company=company, isdeleted=False
            ).values_list('group_id', flat=True))
        except AttributeError:
            log_report_access(request=request, report_type='Group Information',
                              sql_template='', params=[],
                              status=ReportAccessLog.Status.FORBIDDEN)
            return Response({'error': 'User is not associated with a company'}, status=403)

    if not group_ids:
        log_report_access(request=request, report_type='Group Information',
                          sql_template='', params=[],
                          status=ReportAccessLog.Status.NO_DATA)
        return Response({'count': 0, 'results': [], 'message': 'No groups found for this company'})

    queryset = GroupInformation.objects.using('company_external').filter(group_id__in=group_ids)
    serializer = GroupInformationSerializer(queryset, many=True)

    log_report_access(request=request, report_type='Group Information',
                      sql_template='', params=[],
                      status=ReportAccessLog.Status.SUCCESS)
    return Response({'count': queryset.count(), 'group_ids': group_ids, 'results': serializer.data})


class GroupEndowmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only API endpoint for Group Endowment from view_copo_groupEndowment."""
    queryset = GroupEndowment.objects.using('company_external').all()
    serializer_class = GroupEndowmentSerializer
    authentication_classes = _AUTH

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['group_id', 'policy_status', 'fiscal_year', 'gender',
                        'policy_type', 'is_adb', 'register_no', 'employee_id', 'claim_status']
    search_fields = ['name', 'nep_name', 'policy_no', 'employee_id',
                     'mobile', 'email', 'register_no']
    ordering_fields = ['maturity_date', 'doc', 'name', 'premium', 'sum_assured']
    ordering = ['-maturity_date']

    @action(detail=False, methods=['get'])
    def by_company(self, request):
        """GET /api/corporate/endowments/by_company/?company_id=1"""
        company_id = request.query_params.get('company_id')

        if not company_id:
            return Response({'error': 'company_id parameter is required'}, status=400)

        try:
            company_id = int(company_id)
        except ValueError:
            return Response({'error': 'company_id must be a valid integer'}, status=400)

        group_ids = list(PortalGroup.objects.filter(
            company__company_id=company_id,
            isdeleted=False,
        ).values_list('group_id', flat=True))

        if not group_ids:
            return Response({
                'company_id': company_id, 'group_ids': [],
                'endowments': [], 'count': 0,
                'message': 'No groups found for this company',
            })

        endowments = GroupEndowment.objects.using('company_external').filter(
            group_id__in=group_ids
        )
        serializer = self.get_serializer(endowments, many=True)

        return Response({
            'company_id': company_id,
            'group_ids': group_ids,
            'count': endowments.count(),
            'endowments': serializer.data,
        })