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
from api_corporate.reports import REPORTS, ReportError

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
    date_type = request.data.get('date_type', 'ad')  # currently informational

    # --- required param check (400 before touching the DB) -----------------
    if not all([group_id, from_date, to_date]):
        log_report_access(
            request=request,
            report_type='Maturity Forecasting Report',
            sql_template='MaturityForecastingReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response(
            {'error': 'group_id, from_date, and to_date are required'},
            status=400,
        )

    # --- group access check (403 before touching the DB) -------------------
    allowed, error_response = _verify_group_access(request, group_id)
    if not allowed:
        log_report_access(
            request=request,
            report_type='Maturity Forecasting Report',
            sql_template='MaturityForecastingReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.FORBIDDEN,
        )
        return error_response

    # --- dispatch to the Python fetcher ------------------------------------
    try:
        results = REPORTS['maturity_forecasting'](group_id, from_date, to_date)
    except ReportError as e:
        # Clean, user-facing validation error (e.g. bad date format).
        log_report_access(
            request=request,
            report_type='Maturity Forecasting Report',
            sql_template='MaturityForecastingReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.INVALID_INPUT,
            exc=e,
        )
        return Response({'error': e.message}, status=e.status)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(
            request=request,
            report_type='Maturity Forecasting Report',
            sql_template='MaturityForecastingReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response(
            {
                'error': f'Failed to generate report: {e}',
                'details': error_details if request.user.is_superuser else None,
            },
            status=500,
        )

    # --- success -----------------------------------------------------------
    status_val = (
        ReportAccessLog.Status.NO_DATA if not results
        else ReportAccessLog.Status.SUCCESS
    )
    log_report_access(
        request=request,
        report_type='Maturity Forecasting Report',
        sql_template='MaturityForecastingReport',
        params=[group_id, from_date, to_date],
        status=status_val,
    )

    return Response({
        'success': True,
        'count': len(results),
        'group_id': group_id,
        'from_date': from_date,
        'to_date': to_date,
        'date_type': date_type,
        'policies': results,
    })



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def group_transfer_report(request):
    """POST /api/corporate/reports/group-transfer/"""
    group_id           = request.data.get('group_id')
    transfer_date_from = request.data.get('transfer_date_from')
    transfer_date_to   = request.data.get('transfer_date_to')
    date_type          = request.data.get('date_type', 'ad')  # informational

    # --- required param check (400 before touching the DB) -----------------
    if not all([group_id, transfer_date_from, transfer_date_to]):
        log_report_access(
            request=request,
            report_type='Group Transfer Report',
            sql_template='GroupTransferReport',
            params=[group_id, transfer_date_from, transfer_date_to],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response(
            {'error': 'group_id, transfer_date_from, and transfer_date_to are required'},
            status=400,
        )

    # --- group access check (403 before touching the DB) -------------------
    allowed, error_response = _verify_group_access(request, group_id)
    if not allowed:
        log_report_access(
            request=request,
            report_type='Group Transfer Report',
            sql_template='GroupTransferReport',
            params=[group_id, transfer_date_from, transfer_date_to],
            status=ReportAccessLog.Status.FORBIDDEN,
        )
        return error_response

    # --- dispatch to the Python fetcher ------------------------------------
    try:
        results = REPORTS['group_transfer'](
            group_id, transfer_date_from, transfer_date_to,
        )
    except ReportError as e:
        log_report_access(
            request=request,
            report_type='Group Transfer Report',
            sql_template='GroupTransferReport',
            params=[group_id, transfer_date_from, transfer_date_to],
            status=ReportAccessLog.Status.INVALID_INPUT,
            exc=e,
        )
        return Response({'error': e.message}, status=e.status)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(
            request=request,
            report_type='Group Transfer Report',
            sql_template='GroupTransferReport',
            params=[group_id, transfer_date_from, transfer_date_to],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response(
            {
                'error': f'Failed to generate report: {e}',
                'details': error_details if request.user.is_superuser else None,
            },
            status=500,
        )

    # --- success -----------------------------------------------------------
    status_val = (
        ReportAccessLog.Status.NO_DATA if not results
        else ReportAccessLog.Status.SUCCESS
    )
    log_report_access(
        request=request,
        report_type='Group Transfer Report',
        sql_template='GroupTransferReport',
        params=[group_id, transfer_date_from, transfer_date_to],
        status=status_val,
    )

    return Response({
        'success': True,
        'count': len(results),
        'group_id': group_id,
        'transfer_date_from': transfer_date_from,
        'transfer_date_to': transfer_date_to,
        'date_type': date_type,
        'transfers': results,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def loan_repayment_report(request):
    """POST /api/corporate/reports/loan-repayment/"""
    group_id  = request.data.get('group_id')
    from_date = request.data.get('from_date')
    to_date   = request.data.get('to_date')
    date_type = request.data.get('date_type', 'ad')  # informational

    # --- required param check (400 before touching the DB) -----------------
    if not all([group_id, from_date, to_date]):
        log_report_access(
            request=request,
            report_type='Loan Repayment Report',
            sql_template='LoanRepaymentReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response(
            {'error': 'group_id, from_date, and to_date are required'},
            status=400,
        )

    # --- group access check (403 before touching the DB) -------------------
    allowed, error_response = _verify_group_access(request, group_id)
    if not allowed:
        log_report_access(
            request=request,
            report_type='Loan Repayment Report',
            sql_template='LoanRepaymentReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.FORBIDDEN,
        )
        return error_response

    # --- dispatch to the Python fetcher ------------------------------------
    try:
        results = REPORTS['loan_repayment'](group_id, from_date, to_date)
    except ReportError as e:
        log_report_access(
            request=request,
            report_type='Loan Repayment Report',
            sql_template='LoanRepaymentReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.INVALID_INPUT,
            exc=e,
        )
        return Response({'error': e.message}, status=e.status)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(
            request=request,
            report_type='Loan Repayment Report',
            sql_template='LoanRepaymentReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response(
            {
                'error': f'Failed to generate report: {e}',
                'details': error_details if request.user.is_superuser else None,
            },
            status=500,
        )

    # --- success -----------------------------------------------------------
    status_val = (
        ReportAccessLog.Status.NO_DATA if not results
        else ReportAccessLog.Status.SUCCESS
    )
    log_report_access(
        request=request,
        report_type='Loan Repayment Report',
        sql_template='LoanRepaymentReport',
        params=[group_id, from_date, to_date],
        status=status_val,
    )

    return Response({
        'success': True,
        'count': len(results),
        'group_id': group_id,
        'from_date': from_date,
        'to_date': to_date,
        'date_type': date_type,
        'repayments': results,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def policy_detail(request):
    """POST /api/corporate/policy-detail/"""
    policy_no = request.data.get('policy_no')

    if not policy_no:
        log_report_access(
            request=request,
            report_type='Policy Detail',
            sql_template='PolicyDetail',
            params=[policy_no],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response({'error': 'policy_no is required'}, status=400)

    # ── Resolve group_ids (with session caching) ──────────────────────────
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
                    log_report_access(
                        request=request,
                        report_type='Policy Detail',
                        sql_template='PolicyDetail',
                        params=[policy_no],
                        status=ReportAccessLog.Status.FORBIDDEN,
                    )
                    return Response({'error': 'Company account is inactive'}, status=403)
                group_ids = list(PortalGroup.objects.filter(
                    company=company, isdeleted=False
                ).values_list('group_id', flat=True))
            except AttributeError:
                log_report_access(
                    request=request,
                    report_type='Policy Detail',
                    sql_template='PolicyDetail',
                    params=[policy_no],
                    status=ReportAccessLog.Status.FORBIDDEN,
                )
                return Response({'error': 'User is not associated with a company'}, status=403)

        if not group_ids:
            log_report_access(
                request=request,
                report_type='Policy Detail',
                sql_template='PolicyDetail',
                params=[policy_no],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({'error': 'No groups found for your company'}, status=403)

        request.session['company_group_ids'] = group_ids

    # ── Dispatch to the Python fetcher ─────────────────────────────────────
    try:
        data = REPORTS['policy_detail'](policy_no, group_ids)
    except ReportError as e:
        log_report_access(
            request=request,
            report_type='Policy Detail',
            sql_template='PolicyDetail',
            params=[policy_no, *group_ids],
            status=ReportAccessLog.Status.FORBIDDEN if e.status == 403
                   else ReportAccessLog.Status.INVALID_INPUT,
            exc=e,
        )
        return Response({'error': e.message}, status=e.status)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(
            request=request,
            report_type='Policy Detail',
            sql_template='PolicyDetail',
            params=[policy_no, *group_ids],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response(
            {
                'error': f'Failed to fetch policy detail: {e}',
                'details': error_details if request.user.is_superuser else None,
            },
            status=500,
        )

    status_val = (
        ReportAccessLog.Status.NO_DATA
        if not data['summary'] and not data['loans']
        else ReportAccessLog.Status.SUCCESS
    )
    log_report_access(
        request=request,
        report_type='Policy Detail',
        sql_template='PolicyDetail',
        params=[policy_no, *group_ids],
        status=status_val,
    )

    return Response({
        'success': True,
        'policy_no': policy_no,
        'summary': data['summary'],
        'loans': data['loans'],
    })



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def death_claim_report(request):
    """POST /api/corporate/reports/death-claim/"""
    group_id  = request.data.get('group_id')
    from_date = request.data.get('from_date')
    to_date   = request.data.get('to_date')

    # --- required param check (400 before touching the DB) -----------------
    if not all([group_id, from_date, to_date]):
        log_report_access(
            request=request,
            report_type='Death Claim Report',
            sql_template='GroupDeathReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response(
            {'error': 'group_id, from_date, and to_date are required'},
            status=400,
        )

    # --- group access check (403 before touching the DB) -------------------
    allowed, error_response = _verify_group_access(request, group_id)
    if not allowed:
        log_report_access(
            request=request,
            report_type='Death Claim Report',
            sql_template='GroupDeathReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.FORBIDDEN,
        )
        return error_response

    # --- dispatch to the Python fetcher ------------------------------------
    try:
        results = REPORTS['death_claim'](group_id, from_date, to_date)
    except ReportError as e:
        log_report_access(
            request=request,
            report_type='Death Claim Report',
            sql_template='GroupDeathReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.INVALID_INPUT,
            exc=e,
        )
        return Response({'error': e.message}, status=e.status)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(
            request=request,
            report_type='Death Claim Report',
            sql_template='GroupDeathReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response(
            {
                'error': f'Failed to generate death claim report: {e}',
                'details': error_details if request.user.is_superuser else None,
            },
            status=500,
        )

    # --- success (BARE ARRAY response — preserved from existing view) ------
    status_val = (
        ReportAccessLog.Status.NO_DATA if not results
        else ReportAccessLog.Status.SUCCESS
    )
    log_report_access(
        request=request,
        report_type='Death Claim Report',
        sql_template='GroupDeathReport',
        params=[group_id, from_date, to_date],
        status=status_val,
    )

    # NOTE: existing view returns a bare array, not an envelope.
    # Preserved to avoid breaking the frontend. Normalize later if desired.
    return Response(results)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def maturity_claim_report(request):
    """POST /api/corporate/reports/maturity-claim/"""
    group_id  = request.data.get('group_id')
    from_date = request.data.get('from_date')
    to_date   = request.data.get('to_date')

    if not all([group_id, from_date, to_date]):
        log_report_access(
            request=request,
            report_type='Maturity Claim Report',
            sql_template='GroupMaturityReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response(
            {'error': 'group_id, from_date, and to_date are required'},
            status=400,
        )

    allowed, error_response = _verify_group_access(request, group_id)
    if not allowed:
        log_report_access(
            request=request,
            report_type='Maturity Claim Report',
            sql_template='GroupMaturityReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.FORBIDDEN,
        )
        return error_response

    try:
        results = REPORTS['maturity_claim'](group_id, from_date, to_date)
    except ReportError as e:
        log_report_access(
            request=request,
            report_type='Maturity Claim Report',
            sql_template='GroupMaturityReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.INVALID_INPUT,
            exc=e,
        )
        return Response({'error': e.message}, status=e.status)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(
            request=request,
            report_type='Maturity Claim Report',
            sql_template='GroupMaturityReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response(
            {
                'error': f'Failed to generate maturity claim report: {e}',
                'details': error_details if request.user.is_superuser else None,
            },
            status=500,
        )

    status_val = (
        ReportAccessLog.Status.NO_DATA if not results
        else ReportAccessLog.Status.SUCCESS
    )
    log_report_access(
        request=request,
        report_type='Maturity Claim Report',
        sql_template='GroupMaturityReport',
        params=[group_id, from_date, to_date],
        status=status_val,
    )

    return Response(results)



VALID_FLAGS     = {'NB', 'RB'}
VALID_FILTER_BY = {'PaidDate', 'ValueDate'}


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def group_business_detail_report(request):
    """POST /api/corporate/reports/group-business-detail/"""
    VALID_FLAGS     = {'NB', 'RB'}
    VALID_FILTER_BY = {'PaidDate', 'ValueDate'}

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
        log_report_access(
            request=request,
            report_type=report_name,
            sql_template='BusinessDetail',
            params=[group_id, from_date, to_date, filter_by, flag],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response(
            {'error': f'Missing required fields: {", ".join(missing)}'},
            status=400,
        )

    if flag not in VALID_FLAGS:
        log_report_access(
            request=request,
            report_type='Business Detail Report',
            sql_template='BusinessDetail',
            params=[group_id, from_date, to_date, filter_by, flag],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response(
            {'error': f'Invalid flag "{flag}". Must be one of: {", ".join(VALID_FLAGS)}'},
            status=400,
        )

    if filter_by not in VALID_FILTER_BY:
        log_report_access(
            request=request,
            report_type=report_name,
            sql_template='BusinessDetail',
            params=[group_id, from_date, to_date, filter_by, flag],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response(
            {'error': f'Invalid filter_by "{filter_by}". Must be one of: {", ".join(VALID_FILTER_BY)}'},
            status=400,
        )

    allowed, error_response = _verify_group_access(request, group_id)
    if not allowed:
        log_report_access(
            request=request,
            report_type=report_name,
            sql_template='BusinessDetail',
            params=[group_id, from_date, to_date, filter_by, flag],
            status=ReportAccessLog.Status.FORBIDDEN,
        )
        return error_response

    try:
        results = REPORTS['business_detail'](
            group_id, from_date, to_date, filter_by, flag,
        )
    except ReportError as e:
        log_report_access(
            request=request,
            report_type=report_name,
            sql_template='BusinessDetail',
            params=[group_id, from_date, to_date, filter_by, flag],
            status=ReportAccessLog.Status.INVALID_INPUT,
            exc=e,
        )
        return Response({'error': e.message}, status=e.status)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(
            request=request,
            report_type=report_name,
            sql_template='BusinessDetail',
            params=[group_id, from_date, to_date, filter_by, flag],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response(
            {
                'error': f'Failed to generate group business detail report: {e}',
                'details': error_details if request.user.is_superuser else None,
            },
            status=500,
        )

    status_val = (
        ReportAccessLog.Status.NO_DATA if not results
        else ReportAccessLog.Status.SUCCESS
    )
    log_report_access(
        request=request,
        report_type=report_name,
        sql_template='BusinessDetail',
        params=[group_id, from_date, to_date, filter_by, flag],
        status=status_val,
    )

    return Response(results)



@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def surrender_claim_report(request):
    """POST /api/corporate/reports/surrender-claim/"""
    group_id  = request.data.get('group_id')
    from_date = request.data.get('from_date')
    to_date   = request.data.get('to_date')

    if not all([group_id, from_date, to_date]):
        log_report_access(
            request=request,
            report_type='Surrender Claim Report',
            sql_template='GroupSurrenderReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response(
            {'error': 'group_id, from_date, and to_date are required'},
            status=400,
        )

    allowed, error_response = _verify_group_access(request, group_id)
    if not allowed:
        log_report_access(
            request=request,
            report_type='Surrender Claim Report',
            sql_template='GroupSurrenderReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.FORBIDDEN,
        )
        return error_response

    try:
        results = REPORTS['surrender_claim'](group_id, from_date, to_date)
    except ReportError as e:
        log_report_access(
            request=request,
            report_type='Surrender Claim Report',
            sql_template='GroupSurrenderReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.INVALID_INPUT,
            exc=e,
        )
        return Response({'error': e.message}, status=e.status)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(
            request=request,
            report_type='Surrender Claim Report',
            sql_template='GroupSurrenderReport',
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response(
            {
                'error': f'Failed to generate surrender claim report: {e}',
                'details': error_details if request.user.is_superuser else None,
            },
            status=500,
        )

    status_val = (
        ReportAccessLog.Status.NO_DATA if not results
        else ReportAccessLog.Status.SUCCESS
    )
    log_report_access(
        request=request,
        report_type='Surrender Claim Report',
        sql_template='GroupSurrenderReport',
        params=[group_id, from_date, to_date],
        status=status_val,
    )

    return Response(results)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def policy_summary_report(request):
    """POST /api/corporate/reports/policy-summary/"""
    policy_no = request.data.get('policy_no')

    if not policy_no:
        log_report_access(
            request=request,
            report_type='Policy Summary Report',
            sql_template='PolicySummary',
            params=[policy_no],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response({'error': 'policy_no is required'}, status=400)

    # --- Permission: resolve authorized group_ids ---------------------------
    if request.user.is_superuser or request.user.is_staff:
        group_ids = list(PortalGroup.objects.filter(
            isdeleted=False
        ).values_list('group_id', flat=True))
    else:
        company = request.user.company_profile.company

        if not company.isactive:
            log_report_access(
                request=request,
                report_type='Policy Summary Report',
                sql_template='PolicySummary',
                params=[policy_no],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({'error': 'Company account is inactive'}, status=403)

        group_ids = list(PortalGroup.objects.filter(
            company=company, isdeleted=False
        ).values_list('group_id', flat=True))

        if not group_ids:
            log_report_access(
                request=request,
                report_type='Policy Summary Report',
                sql_template='PolicySummary',
                params=[policy_no],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({'error': 'No groups found for your company'}, status=404)

    # --- Dispatch to the Python fetcher ------------------------------------
    try:
        results = REPORTS['policy_summary'](policy_no, group_ids)
    except ReportError as e:
        log_report_access(
            request=request,
            report_type='Policy Summary Report',
            sql_template='PolicySummary',
            params=[policy_no],
            status=ReportAccessLog.Status.INVALID_INPUT,
            exc=e,
        )
        return Response({'error': e.message}, status=e.status)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(
            request=request,
            report_type='Policy Summary Report',
            sql_template='PolicySummary',
            params=[policy_no],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response(
            {
                'error': f'Failed to generate report: {e}',
                'details': error_details if request.user.is_superuser else None,
            },
            status=500,
        )

    status_val = (
        ReportAccessLog.Status.NO_DATA if not results
        else ReportAccessLog.Status.SUCCESS
    )
    log_report_access(
        request=request,
        report_type='Policy Summary Report',
        sql_template='PolicySummary',
        params=[policy_no, *group_ids],
        status=status_val,
    )

    return Response(results)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes(_AUTH)
def surrender_calculator(request):
    """POST /api/corporate/surrender-calculator/"""
    policy_no  = request.data.get('policy_no')
    claim_date = request.data.get('claim_date')

    if not policy_no:
        log_report_access(
            request=request,
            report_type='Surrender Calculator',
            sql_template='SurrenderCalculator',
            params=[policy_no, claim_date],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response({'error': 'policy_no is required'}, status=400)

    # --- Permission: coarse "company has any groups" gate (preserved from
    #     existing view; group_ids not passed to fetch — SP derives GroupId
    #     itself via SELECT TOP 1 GroupId FROM tblGroupEndowment WHERE PolicyNo = ?)
    if request.user.is_superuser or request.user.is_staff:
        group_ids = list(PortalGroup.objects.filter(
            isdeleted=False
        ).values_list('group_id', flat=True))
    else:
        company = request.user.company_profile.company

        if not company.isactive:
            log_report_access(
                request=request,
                report_type='Surrender Calculator',
                sql_template='SurrenderCalculator',
                params=[policy_no, claim_date],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({'error': 'Company account is inactive'}, status=403)

        group_ids = list(PortalGroup.objects.filter(
            company=company, isdeleted=False
        ).values_list('group_id', flat=True))

        if not group_ids:
            log_report_access(
                request=request,
                report_type='Surrender Calculator',
                sql_template='SurrenderCalculator',
                params=[policy_no, claim_date],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({'error': 'No groups found for your company'}, status=404)

    # --- Dispatch to the Python fetcher ------------------------------------
    try:
        results = REPORTS['surrender_calculator'](policy_no, claim_date)
    except ReportError as e:
        log_report_access(
            request=request,
            report_type='Surrender Calculator',
            sql_template='SurrenderCalculator',
            params=[policy_no, claim_date],
            status=ReportAccessLog.Status.INVALID_INPUT,
            exc=e,
        )
        return Response({'error': e.message}, status=e.status)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(
            request=request,
            report_type='Surrender Calculator',
            sql_template='SurrenderCalculator',
            params=[policy_no, claim_date],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response(
            {
                'error': f'Failed to retrieve surrender data: {e}',
                'details': error_details if request.user.is_superuser else None,
            },
            status=500,
        )

    # fetch returns List[Dict] with 0 or 1 element.
    # Existing view returns a single object (not a list) — preserve that.
    if not results:
        log_report_access(
            request=request,
            report_type='Surrender Calculator',
            sql_template='SurrenderCalculator',
            params=[policy_no, claim_date],
            status=ReportAccessLog.Status.NO_DATA,
        )
        return Response({'error': 'Policy not found or access denied'}, status=404)

    log_report_access(
        request=request,
        report_type='Surrender Calculator',
        sql_template='SurrenderCalculator',
        params=[policy_no, claim_date],
        status=ReportAccessLog.Status.SUCCESS,
    )

    return Response(results[0])


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

            # Split into words so each word is searched independently.
            # "UMA PANDEY" → must contain "UMA" AND "PANDEY" somewhere
            # in the concatenated fields. This handles middle names,
            # extra spaces, abbreviations, etc.
            words = query.split()
            search_fields = (
                "(ISNULL(policyNo, '') + ' ' + "
                "ISNULL(name, '') + ' ' + "
                "ISNULL(employeeid, ''))"
            )
            like_clauses = " AND ".join(
                [f"{search_fields} LIKE %s" for _ in words]
            )
            like_params = [f'%{w}%' for w in words]

            sql = f"""
                SELECT DISTINCT TOP 100 policyNo, name, employeeid
                FROM tblGroupEndowment
                WHERE groupId IN ({placeholders})
                AND {like_clauses}
            """
            cursor.execute(sql, group_ids + like_params)
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

    try:
        data = REPORTS['dashboard_data'](group_ids)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        return Response(
            {
                'error': f'Failed to retrieve dashboard data: {e}',
                'details': error_details if request.user.is_superuser else None,
            },
            status=500,
        )

    return Response({
        'company_id': company_id,
        'group_ids': group_ids,
        'summary': data['summary'],
        'latest_policies': data['latest_policies'],
        'fup_data': data['fup_data'],
    })


# ============================================================
# VIEWSETS
# ============================================================

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
                log_report_access(
                    request=request, report_type='Group Information',
                    sql_template='GroupInformation', params=[],
                    status=ReportAccessLog.Status.INVALID_INPUT,
                )
                return Response({'error': 'Invalid company_id'}, status=400)
        else:
            group_ids = list(PortalGroup.objects.filter(
                isdeleted=False
            ).values_list('group_id', flat=True))
    else:
        try:
            company = user.company_profile.company
            if not company.isactive:
                log_report_access(
                    request=request, report_type='Group Information',
                    sql_template='GroupInformation', params=[],
                    status=ReportAccessLog.Status.FORBIDDEN,
                )
                return Response({'error': 'Company account is inactive'}, status=403)
            group_ids = list(PortalGroup.objects.filter(
                company=company, isdeleted=False
            ).values_list('group_id', flat=True))
        except AttributeError:
            log_report_access(
                request=request, report_type='Group Information',
                sql_template='GroupInformation', params=[],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({'error': 'User is not associated with a company'}, status=403)

    if not group_ids:
        log_report_access(
            request=request, report_type='Group Information',
            sql_template='GroupInformation', params=[],
            status=ReportAccessLog.Status.NO_DATA,
        )
        return Response({'count': 0, 'results': [], 'message': 'No groups found for this company'})

    try:
        results = REPORTS['group_information'](group_ids)
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        log_report_access(
            request=request, report_type='Group Information',
            sql_template='GroupInformation', params=group_ids,
            status=ReportAccessLog.Status.ERROR, exc=e,
        )
        return Response(
            {
                'error': f'Failed to fetch group information: {e}',
                'details': error_details if request.user.is_superuser else None,
            },
            status=500,
        )

    log_report_access(
        request=request, report_type='Group Information',
        sql_template='GroupInformation', params=group_ids,
        status=ReportAccessLog.Status.SUCCESS if results
                 else ReportAccessLog.Status.NO_DATA,
    )

    return Response({'count': len(results), 'group_ids': group_ids, 'results': results})


# ── CompanyPoliciesViewSet replacement ──

@api_view(['GET'])
def company_policies_list(request):
    """GET /api/company/policies/
    
    Query params: page, search, policy_status, fiscal_year, gender,
    policy_type, is_adb, employee_id, claim_status, ordering
    """
    company = request.user.company_profile.company
    if not company.isactive:
        return Response({'error': 'Company account is inactive'}, status=403)

    group_ids = list(PortalGroup.objects.filter(
        company=company, isdeleted=False
    ).values_list('group_id', flat=True))

    if not group_ids:
        return Response(
            {'count': 0, 'next': None, 'previous': None, 'results': []}
        )

    # Parse query params
    page = int(request.query_params.get('page', 1))
    search = request.query_params.get('search', '')
    ordering = request.query_params.get('ordering', '-maturity_date')

    filters = {}
    for f in ['policy_status', 'fiscal_year', 'gender', 'policy_type',
              'is_adb', 'employee_id', 'claim_status']:
        v = request.query_params.get(f)
        if v:
            filters[f] = v

    try:
        data = REPORTS['company_policies_list'](
            group_ids=group_ids,
            page=page,
            page_size=100,
            search=search or None,
            filters=filters or None,
            ordering=ordering,
        )
    except Exception as e:
        import traceback
        return Response(
            {
                'error': f'Failed to fetch policies: {e}',
                'details': traceback.format_exc() if request.user.is_superuser else None,
            },
            status=500,
        )

    return Response(data)


@api_view(['POST'])
def company_policies_statistics(request):
    """POST /api/company/policies/statistics/"""
    company = request.user.company_profile.company
    if not company.isactive:
        return Response({'error': 'Company account is inactive'}, status=403)

    group_ids = list(PortalGroup.objects.filter(
        company=company, isdeleted=False
    ).values_list('group_id', flat=True))

    try:
        data = REPORTS['company_policies_statistics'](group_ids)
    except Exception as e:
        import traceback
        return Response(
            {
                'error': f'Failed to fetch statistics: {e}',
                'details': traceback.format_exc() if request.user.is_superuser else None,
            },
            status=500,
        )

    return Response(data)


# ── GroupEndowmentViewSet replacement ──

@api_view(['GET'])
def group_endowment_list(request):
    """GET /api/corporate/endowments/
    
    Query params: page, search, group_id, policy_status, fiscal_year, gender,
    policy_type, is_adb, register_no, employee_id, claim_status, ordering
    """
    if request.user.is_superuser or request.user.is_staff:
        group_ids = list(PortalGroup.objects.filter(
            isdeleted=False
        ).values_list('group_id', flat=True))
    else:
        company = request.user.company_profile.company
        if not company.isactive:
            return Response({'error': 'Company account is inactive'}, status=403)
        group_ids = list(PortalGroup.objects.filter(
            company=company, isdeleted=False
        ).values_list('group_id', flat=True))

    if not group_ids:
        return Response(
            {'count': 0, 'next': None, 'previous': None, 'results': []}
        )

    page = int(request.query_params.get('page', 1))
    search = request.query_params.get('search', '')
    ordering = request.query_params.get('ordering', '-maturity_date')

    filters = {}
    for f in ['group_id', 'policy_status', 'fiscal_year', 'gender',
              'policy_type', 'is_adb', 'register_no', 'employee_id', 'claim_status']:
        v = request.query_params.get(f)
        if v:
            filters[f] = v

    try:
        data = REPORTS['company_policies_list'](
            group_ids=group_ids,
            page=page,
            page_size=100,
            search=search or None,
            filters=filters or None,
            ordering=ordering,
        )
    except Exception as e:
        import traceback
        return Response(
            {
                'error': f'Failed to fetch endowments: {e}',
                'details': traceback.format_exc() if request.user.is_superuser else None,
            },
            status=500,
        )

    return Response(data)


@api_view(['GET'])
def group_endowment_by_company(request):
    """GET /api/corporate/endowments/by_company/?company_id=1"""
    company_id = request.query_params.get('company_id')

    if not company_id:
        return Response({'error': 'company_id parameter is required'}, status=400)

    try:
        company_id = int(company_id)
    except ValueError:
        return Response({'error': 'company_id must be a valid integer'}, status=400)

    group_ids = list(PortalGroup.objects.filter(
        company__company_id=company_id, isdeleted=False
    ).values_list('group_id', flat=True))

    if not group_ids:
        return Response({
            'company_id': company_id, 'group_ids': [],
            'endowments': [], 'count': 0,
            'message': 'No groups found for this company',
        })

    try:
        results = REPORTS['company_policies_by_company'](group_ids)
    except Exception as e:
        import traceback
        return Response(
            {
                'error': f'Failed to fetch endowments: {e}',
                'details': traceback.format_exc() if request.user.is_superuser else None,
            },
            status=500,
        )

    return Response({
        'company_id': company_id,
        'group_ids': group_ids,
        'count': len(results),
        'endowments': results,
    })