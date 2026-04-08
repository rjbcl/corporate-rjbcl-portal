from rest_framework import viewsets, filters, status, serializers  #type: ignore
from rest_framework.permissions import IsAuthenticated #type: ignore
from rest_framework.decorators import action #type: ignore
from rest_framework.response import Response #type: ignore
from rest_framework.authentication import SessionAuthentication, BasicAuthentication #type: ignore
from django_filters.rest_framework import DjangoFilterBackend #type: ignore
from main_system.models import Group as PortalGroup
from rest_framework.permissions import AllowAny, IsAuthenticated #type: ignore
from rest_framework_simplejwt.views import TokenObtainPairView #type: ignore
from rest_framework_simplejwt.authentication import JWTAuthentication #type: ignore
from rest_framework.decorators import api_view, permission_classes, authentication_classes #type: ignore
import django_filters #type: ignore
from .models import GroupEndowment, GroupInformation
from .serializers import (
    GroupEndowmentSerializer, 
    GroupInformationSerializer,
    CustomTokenObtainPairSerializer
)
from .permissions import IsCompanyUser, IsIndividualUser
from django.db import connections #type: ignore
from .utils import log_report_access
from main_system.models import ReportAccessLog


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Custom login view that returns JWT token with user info.
    Only allows company and individual users (not staff).
    """
    permission_classes = (AllowAny,)
    serializer_class = CustomTokenObtainPairSerializer
    
    def post(self, request, *args, **kwargs):
        print(f"Login attempt - Data: {request.data}")
        
        serializer = self.get_serializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
            print("Serializer is valid")
        except serializers.ValidationError as e:
            print(f"Validation error: {e.detail}")
            return Response(
                {'error': 'Invalid credentials', 'details': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )
        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return Response(
                {'error': 'Invalid credentials', 'details': str(e)},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        # Check if user is company 
        user = serializer.user
        user_type = user.get_user_type()
        
        print(f"User type: {user_type}")
        
        if user_type not in ['company']:
            return Response(
                {'error': 'Only company  accounts can access the API'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if company account is active
        if not user.company_profile.isactive:
            return Response(
                {'error': 'Company account is inactive'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        print(f"Login successful for: {user.username}")
        # Return only tokens and username to keep response minimal
        return Response({
            'access': serializer.validated_data.get('access'),
            'refresh': serializer.validated_data.get('refresh'),
            'username': serializer.validated_data.get('username')
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication, SessionAuthentication])
def maturity_forecasting_report(request):
    """
    Generate maturity forecasting report by calling stored procedure.
    POST /api/corporate/reports/maturity-forecasting/
    """
    # Get parameters from request
    group_id = request.data.get('group_id')
    from_date = request.data.get('from_date')
    to_date = request.data.get('to_date')
    date_type = request.data.get('date_type', 'ad')
    # Validate required fields
    if not all([group_id, from_date, to_date]):
        log_report_access(
            request=request,
            report_type='Maturity Forecasting Report',
            sql_template='',
            params=[],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response({
            'error': 'group_id, from_date, and to_date are required'
        }, status=400)
    
    print(f"Report request - Group: {group_id}, From: {from_date}, To: {to_date}, Type: {date_type}")
    
    # Security: Verify the logged-in user owns this group
    if not request.user.is_superuser and not request.user.is_staff:
        company = request.user.company_profile
        group_exists = PortalGroup.objects.filter(
            company_id=company,
            group_id=group_id,
            isdeleted=False
        ).exists()
        
        if not group_exists:
            log_report_access(
                request=request,
                report_type='Maturity Forecasting Report',
                sql_template='',
                params=[],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({
                'error': 'You can only access your own company groups'
            }, status=403)
    
    try:
        results = []
        
        with connections['company_external'].cursor() as cursor:
            # Method 1: Try using raw SQL with SET NOCOUNT ON
            sql = """
                SET NOCOUNT ON;
                EXEC proc_copo_GroupReport 
                    @flag = 'MaturityForecastingReport',
                    @User = 'report_reader',
                    @GroupId = %s,
                    @FromDate = %s,
                    @ToDate = %s;
            """
            
            print(f"Executing: {sql}")
            
            cursor.execute(sql, [group_id, from_date, to_date])
            
            # Process all result sets
            result_set_count = 0
            while True:
                result_set_count += 1
                print(f"Processing result set {result_set_count}")
                
                if cursor.description:
                    columns = [col[0] for col in cursor.description]                    
                    rows = cursor.fetchall()
                    print(f"Rows in result set {result_set_count}: {len(rows)}")
                    
                    for row in rows:
                        row_dict = {}
                        for i, value in enumerate(row):
                            col_name = columns[i]
                            # Handle different data types
                            if value is None:
                                row_dict[col_name] = None
                            elif hasattr(value, 'isoformat'):  # datetime
                                row_dict[col_name] = value.isoformat()
                            elif isinstance(value, (int, float)):
                                row_dict[col_name] = value
                            else:
                                row_dict[col_name] = str(value)
                        results.append(row_dict)
                else:
                    print(f"Result set {result_set_count} has no description (no columns)")
                
                # Try to move to next result set
                if not cursor.nextset():
                    print("No more result sets")
                    break
            
            print(f"Total results collected: {len(results)}")
        
        if not results:
            print("WARNING: No results returned from stored procedure")
            log_report_access(
                request=request,
                report_type='Maturity Forecasting Report',
                sql_template=sql,
                params=[group_id, from_date, to_date],
                status=ReportAccessLog.Status.NO_DATA,
            )
            return Response({
                'success': True,
                'count': 0,
                'group_id': group_id,
                'from_date': from_date,
                'to_date': to_date,
                'date_type': date_type,
                'policies': [],
                'message': 'No policies found for the given criteria. The stored procedure executed successfully but returned no data.'
            })
        
        log_report_access(
            request=request,
            report_type='Maturity Forecasting Report',
            sql_template=sql,
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.SUCCESS,
        )
        return Response({
            'success': True,
            'count': len(results),
            'group_id': group_id,
            'from_date': from_date,
            'to_date': to_date,
            'date_type': date_type,
            'policies': results
        })
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR: {str(e)}")
        print(f"Full traceback:\n{error_details}")
        log_report_access(
            request=request,
            report_type='Maturity Forecasting Report',
            sql_template=sql,
            params=[group_id, from_date, to_date],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response({
            'error': f'Failed to generate report: {str(e)}',
            'details': error_details if request.user.is_superuser else None
        }, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication, SessionAuthentication])
def group_transfer_report(request):
    """
    Generate group transfer report by calling stored procedure.
    POST /api/corporate/reports/group-transfer/
    """
    group_id = request.data.get('group_id')
    transfer_date_from = request.data.get('transfer_date_from')
    transfer_date_to = request.data.get('transfer_date_to')
    date_type = request.data.get('date_type', 'ad')

    if not all([group_id, transfer_date_from, transfer_date_to]):
        log_report_access(
            request=request,
            report_type='Group Transfer Report',
            sql_template='',
            params=[],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response({
            'error': 'group_id, transfer_date_from, and transfer_date_to are required'
        }, status=400)

    print(f"Report request - Group: {group_id}, From: {transfer_date_from}, To: {transfer_date_to}, Type: {date_type}")

    if not request.user.is_superuser and not request.user.is_staff:
        company = request.user.company_profile
        group_exists = PortalGroup.objects.filter(
            company_id=company,
            group_id=group_id,
            isdeleted=False
        ).exists()

        if not group_exists:
            log_report_access(
                request=request,
                report_type='Group Transfer Report',
                sql_template='',
                params=[],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({
                'error': 'You can only access your own company groups'
            }, status=403)

    try:
        results = []

        with connections['company_external'].cursor() as cursor:
            sql = """
                SET NOCOUNT ON;
                EXEC proc_copo_GroupReport
                    @flag = 'GroupTransferReport',
                    @User = 'report_reader_copo',
                    @GroupId = %s,
                    @TransferDateFrom = %s,
                    @TransferDateTo = %s;
            """

            cursor.execute(sql, [group_id, transfer_date_from, transfer_date_to])

            result_set_count = 0
            while True:
                result_set_count += 1
                print(f"Processing result set {result_set_count}")

                if cursor.description:
                    columns = [col[0] for col in cursor.description]
                    rows = cursor.fetchall()
                    print(f"Rows in result set {result_set_count}: {len(rows)}")

                    for row in rows:
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
                        results.append(row_dict)
                else:
                    print(f"Result set {result_set_count} has no description (no columns)")

                if not cursor.nextset():
                    print("No more result sets")
                    break

            print(f"Total results collected: {len(results)}")

        if not results:
            log_report_access(
                request=request,
                report_type='Group Transfer Report',
                sql_template=sql,
                params=[group_id, transfer_date_from, transfer_date_to],
                status=ReportAccessLog.Status.NO_DATA,
            )
            return Response({
                'success': True,
                'count': 0,
                'group_id': group_id,
                'transfer_date_from': transfer_date_from,
                'transfer_date_to': transfer_date_to,
                'date_type': date_type,
                'transfers': [],
                'message': 'No transfers found for the given criteria. The stored procedure executed successfully but returned no data.'
            })

        log_report_access(
            request=request,
            report_type='Group Transfer Report',
            sql_template=sql,
            params=[group_id, transfer_date_from, transfer_date_to],
            status=ReportAccessLog.Status.SUCCESS,
        )
        return Response({
            'success': True,
            'count': len(results),
            'group_id': group_id,
            'transfer_date_from': transfer_date_from,
            'transfer_date_to': transfer_date_to,
            'date_type': date_type,
            'transfers': results
        })

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR: {str(e)}")
        print(f"Full traceback:\n{error_details}")
        log_report_access(
            request=request,
            report_type='Group Transfer Report',
            sql_template=sql,
            params=[group_id, transfer_date_from, transfer_date_to],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response({
            'error': f'Failed to generate report: {str(e)}',
            'details': error_details if request.user.is_superuser else None
        }, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication, SessionAuthentication])
def loan_repayment_report(request):
    """
    Generate loan repayment report by calling stored procedure.
    POST /api/corporate/reports/loan-repayment/
    """

    # Get parameters from request
    group_id = request.data.get('group_id')
    from_date = request.data.get('from_date')
    to_date = request.data.get('to_date')
    date_type = request.data.get('date_type', 'ad')

    # Validate required fields
    if not all([group_id, from_date, to_date]):
        log_report_access(
            request=request,
            report_type='Loan Repayment Report',
            sql_template='',
            params=[],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response({
            'error': 'group_id, from_date, and to_date are required'
        }, status=400)

    print(f"Report request - Group: {group_id}, From: {from_date}, To: {to_date}, Type: {date_type}")

    # Security: Verify the logged-in user owns this group
    if not request.user.is_superuser and not request.user.is_staff:
        company = request.user.company_profile
        group_exists = PortalGroup.objects.filter(
            company_id=company,
            group_id=group_id,
            isdeleted=False
        ).exists()

        if not group_exists:
            log_report_access(
                request=request,
                report_type='Loan Repayment Report',
                sql_template='',
                params=[],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({
                'error': 'You can only access your own company groups'
            }, status=403)

    try:
        results = []

        with connections['company_external'].cursor() as cursor:
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

            print(f"Executing loan repayment report: {sql}")

            cursor.execute(sql, [from_date, to_date, group_id])

            # Process all result sets
            result_set_count = 0
            while True:
                result_set_count += 1
                print(f"Processing result set {result_set_count}")

                if cursor.description:
                    columns = [col[0] for col in cursor.description]
                    rows = cursor.fetchall()
                    print(f"Rows in result set {result_set_count}: {len(rows)}")

                    for row in rows:
                        row_dict = {}
                        for i, value in enumerate(row):
                            col_name = columns[i]
                            if value is None:
                                row_dict[col_name] = None
                            elif hasattr(value, 'isoformat'):  # datetime
                                row_dict[col_name] = value.isoformat()
                            elif isinstance(value, (int, float)):
                                row_dict[col_name] = value
                            else:
                                row_dict[col_name] = str(value)
                        results.append(row_dict)
                else:
                    print(f"Result set {result_set_count} has no description (no columns)")

                if not cursor.nextset():
                    print("No more result sets")
                    break

            print(f"Total results collected: {len(results)}")

        if not results:
            print("WARNING: No results returned from stored procedure")
            log_report_access(
                request=request,
                report_type='Loan Repayment Report',
                sql_template=sql,
                params=[from_date, to_date, group_id],
                status=ReportAccessLog.Status.NO_DATA,
            )
            return Response({
                'success': True,
                'count': 0,
                'group_id': group_id,
                'from_date': from_date,
                'to_date': to_date,
                'date_type': date_type,
                'repayments': [],
                'message': 'No repayments found for the given criteria. The stored procedure executed successfully but returned no data.'
            })

        log_report_access(
            request=request,
            report_type='Loan Repayment Report',
            sql_template=sql,
            params=[from_date, to_date, group_id],
            status=ReportAccessLog.Status.SUCCESS,
        )
        return Response({
            'success': True,
            'count': len(results),
            'group_id': group_id,
            'from_date': from_date,
            'to_date': to_date,
            'date_type': date_type,
            'repayments': results
        })

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR: {str(e)}")
        print(f"Full traceback:\n{error_details}")
        log_report_access(
            request=request,
            report_type='Loan Repayment Report',
            sql_template=sql,
            params=[from_date, to_date, group_id],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response({
            'error': f'Failed to generate report: {str(e)}',
            'details': error_details if request.user.is_superuser else None
        }, status=500)
    
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication, SessionAuthentication])
def death_claim_report(request):
    """
    Generate death claim report by calling stored procedure.
    POST /api/corporate/reports/death-claim/
    """
    
    group_id = request.data.get('group_id')
    from_date = request.data.get('from_date')
    to_date = request.data.get('to_date')
    
    print(f"Death Claim Report - Group: {group_id}, From: {from_date}, To: {to_date}")
    
    if not all([group_id, from_date, to_date]):
        log_report_access(
            request=request,
            report_type='Death Claim Report',
            sql_template='',
            params=[],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response({
            'error': 'group_id, from_date, and to_date are required'
        }, status=400)
    
    if not request.user.is_superuser and not request.user.is_staff:
        company = request.user.company_profile
        group_exists = PortalGroup.objects.filter(
            company_id=company,
            group_id=group_id,
            isdeleted=False
        ).exists()
        
        if not group_exists:
            log_report_access(
                request=request,
                report_type='Death Claim Report',
                sql_template='',
                params=[],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({
                'error': 'You can only access your own company groups'
            }, status=403)
    
    try:
        results = []
        
        with connections['company_external'].cursor() as cursor:
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
            
            cursor.execute(sql, [from_date, to_date, group_id])
            
            result_set_count = 0
            while True:
                result_set_count += 1
                
                if cursor.description:
                    columns = [col[0] for col in cursor.description]                    
                    rows = cursor.fetchall()
                    
                    for row in rows:
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
                        results.append(row_dict)
                
                if not cursor.nextset():
                    break

        if not results:
            log_report_access(
                request=request,
                report_type='Death Claim Report',
                sql_template=sql,
                params=[from_date, to_date, group_id],
                status=ReportAccessLog.Status.NO_DATA,
            )
        else:
            log_report_access(
                request=request,
                report_type='Death Claim Report',
                sql_template=sql,
                params=[from_date, to_date, group_id],
                status=ReportAccessLog.Status.SUCCESS,
            )
        return Response(results)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR: {str(e)}\n{error_details}")
        log_report_access(
            request=request,
            report_type='Death Claim Report',
            sql_template=sql,
            params=[from_date, to_date, group_id],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response({
            'error': f'Failed to generate death claim report: {str(e)}',
            'details': error_details if request.user.is_superuser else None
        }, status=500)
    

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication, SessionAuthentication])
def maturity_claim_report(request):
    """
    Generate maturity claim report by calling stored procedure.
    POST /api/corporate/reports/maturity-claim/
    """
    
    group_id = request.data.get('group_id')
    from_date = request.data.get('from_date')
    to_date = request.data.get('to_date')
    
    print(f"Maturity Claim Report - Group: {group_id}, From: {from_date}, To: {to_date}")
    
    if not all([group_id, from_date, to_date]):
        log_report_access(
            request=request,
            report_type='Maturity Claim Report',
            sql_template='',
            params=[],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response({
            'error': 'group_id, from_date, and to_date are required'
        }, status=400)
    
    if not request.user.is_superuser and not request.user.is_staff:
        company = request.user.company_profile
        group_exists = PortalGroup.objects.filter(
            company_id=company,
            group_id=group_id,
            isdeleted=False
        ).exists()
        
        if not group_exists:
            log_report_access(
                request=request,
                report_type='Maturity Claim Report',
                sql_template='',
                params=[],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({
                'error': 'You can only access your own company groups'
            }, status=403)
    
    try:
        results = []
        
        with connections['company_external'].cursor() as cursor:
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
            
            cursor.execute(sql, [from_date, to_date, group_id])
            
            result_set_count = 0
            while True:
                result_set_count += 1
                
                if cursor.description:
                    columns = [col[0] for col in cursor.description]                    
                    rows = cursor.fetchall()
                    
                    for row in rows:
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
                        results.append(row_dict)
                
                if not cursor.nextset():
                    break

        if not results:
            log_report_access(
                request=request,
                report_type='Maturity Claim Report',
                sql_template=sql,
                params=[from_date, to_date, group_id],
                status=ReportAccessLog.Status.NO_DATA,
            )
        else:
            log_report_access(
                request=request,
                report_type='Maturity Claim Report',
                sql_template=sql,
                params=[from_date, to_date, group_id],
                status=ReportAccessLog.Status.SUCCESS,
            )
        return Response(results)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR: {str(e)}\n{error_details}")
        log_report_access(
            request=request,
            report_type='Maturity Claim Report',
            sql_template=sql,
            params=[from_date, to_date, group_id],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response({
            'error': f'Failed to generate maturity claim report: {str(e)}',
            'details': error_details if request.user.is_superuser else None
        }, status=500)
    
VALID_FLAGS     = {'NB', 'RB'}
VALID_FILTER_BY = {'PaidDate', 'ValueDate'}
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication, SessionAuthentication])
def group_business_detail_report(request):
    """
    Generate group new or renewal business report via stored procedure.
    POST /api/corporate/reports/group-business-detail/

    Body params:
        group_id    (required)
        flag        (required) - 'NB' for new business, 'RB' for renewal business
        filter_by   (required) - 'PaidDate' or 'ValueDate'
        from_date   (required)
        to_date     (required)
    """

    group_id  = request.data.get('group_id')
    flag      = request.data.get('flag')
    filter_by = request.data.get('filter_by')
    from_date = request.data.get('from_date')
    to_date   = request.data.get('to_date')

    print(
        f"Group Business Detail Report - Group: {group_id}, Flag: {flag}, "
        f"FilterBy: {filter_by}, From: {from_date}, To: {to_date}"
    )

    # --- Validation ---

    # Build params dict once for reuse in all log calls
    log_params = {'group_id': group_id, 'flag': flag, 'filter_by': filter_by, 'from_date': from_date, 'to_date': to_date}

    missing = [
        field for field, value in {
            'group_id' : group_id,
            'flag'     : flag,
            'filter_by': filter_by,
            'from_date': from_date,
            'to_date'  : to_date,
        }.items() if not value
    ]
    if missing:
        log_report_access(
            request=request,
            report_type='New Business Detail Report' if flag == 'NB' else 'Renewal Business Detail Report',
            sql_template='',
            params=[],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response(
            {'error': f'Missing required fields: {", ".join(missing)}'},
            status=400
        )

    if flag not in VALID_FLAGS:
        log_report_access(
            request=request,
            report_type='Business Detail Report',
            sql_template='',
            params=[],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response(
            {'error': f'Invalid flag "{flag}". Must be one of: {", ".join(VALID_FLAGS)}'},
            status=400
        )

    if filter_by not in VALID_FILTER_BY:
        log_report_access(
            request=request,
            report_type='New Business Detail Report' if flag == 'NB' else 'Renewal Business Detail Report',
            sql_template='',
            params=[],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response(
            {'error': f'Invalid filter_by "{filter_by}". Must be one of: {", ".join(VALID_FILTER_BY)}'},
            status=400
        )

    # Resolve human-readable report name from flag
    report_name = 'New Business Detail Report' if flag == 'NB' else 'Renewal Business Detail Report'

    # --- Group access check ---

    if not request.user.is_superuser and not request.user.is_staff:
        company = request.user.company_profile
        group_exists = PortalGroup.objects.filter(
            company_id=company,
            group_id=group_id,
            isdeleted=False
        ).exists()

        if not group_exists:
            log_report_access(
                request=request,
                report_type=report_name,
                sql_template='',
                params=[],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response(
                {'error': 'You can only access your own company groups'},
                status=403
            )

    # --- Query ---

    try:
        results = []

        with connections['company_external'].cursor() as cursor:
            sql = """
                SET NOCOUNT ON;
                EXEC proc_copo_BusinessDetail
                    @GroupId  = %s,
                    @FromDate = %s,
                    @ToDate   = %s,
                    @FilterBy = %s,
                    @Flag     = %s;
            """

            cursor.execute(sql, [group_id, from_date, to_date, filter_by, flag])

            result_set_count = 0
            while True:
                result_set_count += 1

                if cursor.description:
                    columns = [col[0] for col in cursor.description]
                    rows    = cursor.fetchall()

                    for row in rows:
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
                        results.append(row_dict)

                if not cursor.nextset():
                    break

        log_report_access(
            request=request,
            report_type=report_name,
            sql_template=sql,
            params=[group_id, from_date, to_date, filter_by, flag],
            status=ReportAccessLog.Status.NO_DATA if not results else ReportAccessLog.Status.SUCCESS,
        )
        return Response(results)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR: {str(e)}\n{error_details}")
        log_report_access(
            request=request,
            report_type=report_name,
            sql_template=sql,
            params=[group_id, from_date, to_date, filter_by, flag],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response({
            'error': f'Failed to generate group business detail report: {str(e)}',
            'details': error_details if request.user.is_superuser else None
        }, status=500)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication, SessionAuthentication])
def surrender_claim_report(request):
    """
    Generate surrender claim report by calling stored procedure.
    POST /api/corporate/reports/surrender-claim/
    """
    
    group_id = request.data.get('group_id')
    from_date = request.data.get('from_date')
    to_date = request.data.get('to_date')
    
    print(f"Surrender Claim Report - Group: {group_id}, From: {from_date}, To: {to_date}")
    
    if not all([group_id, from_date, to_date]):
        log_report_access(
            request=request,
            report_type='Surrender Claim Report',
            sql_template='',
            params=[],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response({
            'error': 'group_id, from_date, and to_date are required'
        }, status=400)
    
    if not request.user.is_superuser and not request.user.is_staff:
        company = request.user.company_profile
        group_exists = PortalGroup.objects.filter(
            company_id=company,
            group_id=group_id,
            isdeleted=False
        ).exists()
        
        if not group_exists:
            log_report_access(
                request=request,
                report_type='Surrender Claim Report',
                sql_template='',
                params=[],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({
                'error': 'You can only access your own company groups'
            }, status=403)
    
    try:
        results = []
        
        with connections['company_external'].cursor() as cursor:
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
            
            cursor.execute(sql, [from_date, to_date, group_id])
            
            result_set_count = 0
            while True:
                result_set_count += 1
                
                if cursor.description:
                    columns = [col[0] for col in cursor.description]                    
                    rows = cursor.fetchall()
                    
                    for row in rows:
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
                        results.append(row_dict)
                
                if not cursor.nextset():
                    break

        log_report_access(
            request=request,
            report_type='Surrender Claim Report',
            sql_template=sql,
            params=[from_date, to_date, group_id],
            status=ReportAccessLog.Status.NO_DATA if not results else ReportAccessLog.Status.SUCCESS,
        )
        return Response(results)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR: {str(e)}\n{error_details}")
        log_report_access(
            request=request,
            report_type='Surrender Claim Report',
            sql_template=sql,
            params=[from_date, to_date, group_id],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response({
            'error': f'Failed to generate surrender claim report: {str(e)}',
            'details': error_details if request.user.is_superuser else None
        }, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication, SessionAuthentication])
def policy_summary_report(request):
    """
    Get policy summary data from view_copo_policySummary.
    POST /api/corporate/reports/policy-summary/
    """
    
    policy_no = request.data.get('policy_no')
    
    print(f"Policy Summary Report - Policy: {policy_no}")
    
    if not policy_no:
        log_report_access(
            request=request,
            report_type='Policy Summary Report',
            sql_template='',
            params=[],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response({
            'error': 'policy_no is required'
        }, status=400)
    
    # Get company's group IDs
    if request.user.is_superuser or request.user.is_staff:
        # Superuser/staff can see all groups
        group_ids = list(PortalGroup.objects.filter(
            isdeleted=False
        ).values_list('group_id', flat=True))
    else:
        company = request.user.company_profile
        
        # Check if company account is active
        if not company.isactive:
            log_report_access(
                request=request,
                report_type='Policy Summary Report',
                sql_template='',
                params=[],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({
                'error': 'Company account is inactive'
            }, status=403)
        
        # Get all group_ids for this company
        group_ids = list(PortalGroup.objects.filter(
            company_id=company,
            isdeleted=False
        ).values_list('group_id', flat=True))
        
        if not group_ids:
            log_report_access(
                request=request,
                report_type='Policy Summary Report',
                sql_template='',
                params=[],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({
                'error': 'No groups found for your company'
            }, status=404)
    
    try:
        results = []
        
        with connections['company_external'].cursor() as cursor:
            placeholders = ','.join(['%s'] * len(group_ids))
            sql = f"""
                SELECT * FROM view_copo_policySummary
                WHERE PolicyNo = %s AND GroupId IN ({placeholders})
            """
            
            params = [policy_no] + group_ids
            cursor.execute(sql, params)
            
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                
                for row in rows:
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
                    results.append(row_dict)

        log_report_access(
            request=request,
            report_type='Policy Summary Report',
            sql_template=sql,
            params=params,
            status=ReportAccessLog.Status.NO_DATA if not results else ReportAccessLog.Status.SUCCESS,
        )
        return Response(results)
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR: {str(e)}")
        print(f"Full traceback:\n{error_details}")
        log_report_access(
            request=request,
            report_type='Policy Summary Report',
            sql_template=sql,
            params=params,
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response({
            'error': f'Failed to generate report: {str(e)}',
            'details': error_details if request.user.is_superuser else None
        }, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication, SessionAuthentication])
def surrender_calculator(request):
    """
    Get surrender value and active loan status for a given policy.
    POST /api/corporate/surrender-calculator/
    
    Request body:
        { "policy_no": "05208669" }

    Response:
        {
            "policyNO": "05208669",
            "hasActiveLoan": 1,
            "SurrenderAmount": 50000.00
        }
    """

    policy_no = request.data.get('policy_no')
    if not policy_no:
        log_report_access(
            request=request,
            report_type='Surrender Calculator',
            sql_template='',
            params=[],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response({'error': 'policy_no is required'}, status=400)

    # ----------------------------------------------------------------
    # Resolve accessible group IDs for the requesting user
    # ----------------------------------------------------------------
    if request.user.is_superuser or request.user.is_staff:
        group_ids = list(PortalGroup.objects.filter(
            isdeleted=False
        ).values_list('group_id', flat=True))
    else:
        company = request.user.company_profile

        if not company.isactive:
            log_report_access(
                request=request,
                report_type='Surrender Calculator',
                sql_template='',
                params=[],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({'error': 'Company account is inactive'}, status=403)

        group_ids = list(PortalGroup.objects.filter(
            company_id=company,
            isdeleted=False
        ).values_list('group_id', flat=True))

        if not group_ids:
            log_report_access(
                request=request,
                report_type='Surrender Calculator',
                sql_template='',
                params=[],
                status=ReportAccessLog.Status.FORBIDDEN,
            )
            return Response({'error': 'No groups found for your company'}, status=404)

    # ----------------------------------------------------------------
    # Query the view
    # ----------------------------------------------------------------
    sql = ''
    params = []

    try:
        with connections['company_external'].cursor() as cursor:
            placeholders = ','.join(['%s'] * len(group_ids))
            sql = f"""
                SELECT policyNO, hasActiveLoan, SurrenderAmount
                FROM view_copo_surrender_calculator
                WHERE policyNO = %s AND GroupId IN ({placeholders})
            """
            params = [policy_no] + group_ids
            cursor.execute(sql, params)

            row = cursor.fetchone()

            if not row:
                log_report_access(
                    request=request,
                    report_type='Surrender Calculator',
                    sql_template=sql,
                    params=params,
                    status=ReportAccessLog.Status.NO_DATA,
                )
                return Response({'error': 'Policy not found or access denied'}, status=404)

            columns = [col[0] for col in cursor.description]
            result = {}
            for i, value in enumerate(row):
                col_name = columns[i]
                if value is None:
                    result[col_name] = None
                elif hasattr(value, 'isoformat'):
                    result[col_name] = value.isoformat()
                elif isinstance(value, (int, float)):
                    result[col_name] = value
                else:
                    result[col_name] = str(value)

        log_report_access(
            request=request,
            report_type='Surrender Calculator',
            sql_template=sql,
            params=params,
            status=ReportAccessLog.Status.SUCCESS,
        )
        return Response(result)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR in surrender_calculator: {str(e)}")
        print(f"Full traceback:\n{error_details}")
        log_report_access(
            request=request,
            report_type='Surrender Calculator',
            sql_template=sql,
            params=params,
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response({
            'error': f'Failed to retrieve surrender data: {str(e)}',
            'details': error_details if request.user.is_superuser else None
        }, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication, SessionAuthentication])
def policy_search(request):
    """
    Search policies by policy number or name.
    GET /api/corporate/reports/policy-search/?q=<query>
    """

    query = request.data.get('q', '').strip()

    if not query:
        return Response([], status=200)

    # Check if group_ids are cached in session
    group_ids = request.session.get('company_group_ids')

    if not group_ids:
        if request.user.is_superuser or request.user.is_staff:
            group_ids = list(PortalGroup.objects.filter(
                isdeleted=False
            ).values_list('group_id', flat=True))
        else:
            try:
                company = request.user.company_profile

                if not company.isactive:
                    return Response({'error': 'Company account is inactive'}, status=403)

                group_ids = list(PortalGroup.objects.filter(
                    company_id=company,
                    isdeleted=False
                ).values_list('group_id', flat=True))

            except AttributeError:
                return Response({'error': 'User is not associated with a company'}, status=403)

        if not group_ids:
            return Response([], status=200)

        # Cache in session
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
            params = group_ids + [f'%{query}%']

            cursor.execute(sql, params)
            rows = cursor.fetchall()

        results = [{'policyNo': row[0], 'name': row[1], 'employeeid': row[2]} for row in rows]
        return Response(results, status=200)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR: {str(e)}")
        print(f"Full traceback:\n{error_details}")
        return Response({
            'error': f'Search failed: {str(e)}',
            'details': error_details if request.user.is_superuser else None
        }, status=500)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication, SessionAuthentication])
def policy_loans(request):
    """
    Get loan details for a policy from tblGroupPolicyLoanDetail.
    POST /api/corporate/reports/policy-loans/
    """
    policy_no = request.data.get('policy_no')

    if not policy_no:
        log_report_access(
            request=request,
            report_type='Policy Loans Report',
            sql_template='',
            params=[],
            status=ReportAccessLog.Status.INVALID_INPUT,
        )
        return Response({'error': 'policy_no is required'}, status=400)

    # Get group_ids from session or fetch and cache
    group_ids = request.session.get('company_group_ids')

    if not group_ids:
        if request.user.is_superuser or request.user.is_staff:
            group_ids = list(PortalGroup.objects.filter(
                isdeleted=False
            ).values_list('group_id', flat=True))
        else:
            try:
                company = request.user.company_profile

                if not company.isactive:
                    log_report_access(
                        request=request,
                        report_type='Policy Loans Report',
                        sql_template='',
                        params=[],
                        status=ReportAccessLog.Status.FORBIDDEN,
                    )
                    return Response({'error': 'Company account is inactive'}, status=403)

                group_ids = list(PortalGroup.objects.filter(
                    company_id=company,
                    isdeleted=False
                ).values_list('group_id', flat=True))

            except AttributeError:
                log_report_access(
                    request=request,
                    report_type='Policy Loans Report',
                    sql_template='',
                    params=[],
                    status=ReportAccessLog.Status.FORBIDDEN,
                )
                return Response({'error': 'User is not associated with a company'}, status=403)

        if not group_ids:
            return Response([], status=200)

        request.session['company_group_ids'] = group_ids

    try:
        with connections['company_external'].cursor() as cursor:
            # Security: verify the policy belongs to one of the company's groups
            # before returning loan details
            placeholders = ','.join(['%s'] * len(group_ids))
            verify_sql = f"""
                SELECT COUNT(1) FROM tblGroupEndowment
                WHERE policyNo = %s AND groupId IN ({placeholders})
            """
            cursor.execute(verify_sql, [policy_no] + group_ids)
            count = cursor.fetchone()[0]

            if count == 0:
                log_report_access(
                    request=request,
                    report_type='Policy Loans Report',
                    sql_template=verify_sql,
                    params=[policy_no] + group_ids,
                    status=ReportAccessLog.Status.FORBIDDEN,
                )
                return Response({'error': 'Policy not found or access denied'}, status=403)

            # Fetch loan details
            loan_sql = """
                SELECT
                    PolicyNo,
                    loanID,
                    LoanDate,
                    LoanAmount,
                    InterestRate,
                    Instalment,
                    Status,
                    LastPaidDate,
                    VoucherNo
                FROM tblGroupPolicyLoanDetail
                WHERE policyNo = %s
            """
            cursor.execute(loan_sql, [policy_no])

            if cursor.description:
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()

                results = []
                for row in rows:
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
                    results.append(row_dict)

                log_report_access(
                    request=request,
                    report_type='Policy Loans Report',
                    sql_template=loan_sql,
                    params=[policy_no],
                    status=ReportAccessLog.Status.NO_DATA if not results else ReportAccessLog.Status.SUCCESS,
                )
                return Response(results, status=200)

            log_report_access(
                request=request,
                report_type='Policy Loans Report',
                sql_template=loan_sql,
                params=[policy_no],
                status=ReportAccessLog.Status.NO_DATA,
            )
            return Response([], status=200)

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"ERROR: {str(e)}")
        print(f"Full traceback:\n{error_details}")
        log_report_access(
            request=request,
            report_type='Policy Loans Report',
            sql_template='',
            params=[],
            status=ReportAccessLog.Status.ERROR,
            exc=e,
        )
        return Response({
            'error': f'Failed to fetch loan details: {str(e)}',
            'details': error_details if request.user.is_superuser else None
        }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def company_policies_web(request):
    """
    Web dashboard endpoint - uses Django session authentication.
    GET /api/corporate/endowments/by_company/?company_id=<id>
    """

    company_id = request.query_params.get('company_id', None)

    if not company_id:
        return Response({
            'error': 'company_id parameter is required',
            'example': '/api/corporate/endowments/by_company/?company_id=1'
        }, status=400)

    try:
        company_id = int(company_id)
    except ValueError:
        return Response({
            'error': 'company_id must be a valid integer'
        }, status=400)

    if not request.user.is_superuser and not request.user.is_staff:
        user_company_id = request.user.company_profile.company_id
        if user_company_id != company_id:
            return Response({
                'error': 'You can only access your own company data'
            }, status=403)

    portal_groups = PortalGroup.objects.filter(
        company_id=company_id,
        isdeleted=False
    )

    group_ids = list(portal_groups.values_list('group_id', flat=True))

    if not group_ids:
        return Response({
            'company_id': company_id,
            'group_ids': [],
            'summary': {},
            'latest_policies': [],
            'fup_data': [],
            'message': 'No groups found for this company'
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

class CompanyPoliciesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for company users to access their policies.
    Automatically filters by authenticated company.
    JWT authentication only.
    """
    serializer_class = GroupEndowmentSerializer
    permission_classes = [IsAuthenticated, IsCompanyUser]
    authentication_classes = [JWTAuthentication]  # JWT only for external API
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = [
        'policy_status',
        'fiscal_year',
        'gender',
        'policy_type',
        'is_adb',
        'register_no',
        'employee_id',
        'claim_status',
        'branch'
    ]
    
    search_fields = [
        'name',
        'nep_name',
        'policy_no',
        'employee_id',
        'mobile',
        'email',
        'register_no',
    ]
    
    ordering_fields = [
        'maturity_date',
        'doc',
        'name',
        'premium',
        'sum_assured',
    ]
    
    ordering = ['-maturity_date']
    
    def get_queryset(self):
        """
        Automatically filter policies by the authenticated company's groups.
        """
        user = self.request.user
        
        # Get company from authenticated user
        company = user.company_profile
        
        # Get all group IDs for this company
        group_ids = list(PortalGroup.objects.filter(
            company_id=company,
            isdeleted=False
        ).values_list('group_id', flat=True))
        
        # Return policies for those groups
        return GroupEndowment.objects.using('company_external').filter(
            group_id__in=group_ids
        )
    
    @action(detail=False, methods=['POST'])
    def statistics(self, request):
        """
        Get statistics for the company's policies.
        GET /api/company/policies/statistics/
        """
        queryset = self.get_queryset()
        
        total_policies = queryset.count()
        active_policies = queryset.filter(policy_status='A').count()
        lapsed_policies = queryset.filter(policy_status='L').count()
        
        total_sum_assured = sum(
            float(p.sum_assured or 0) for p in queryset
        )
        total_premium = sum(
            float(p.premium or 0) for p in queryset
        )
        
        return Response({
            'total_policies': total_policies,
            'active_policies': active_policies,
            'lapsed_policies': lapsed_policies,
            'inactive_policies': total_policies - active_policies - lapsed_policies,
            'total_sum_assured': total_sum_assured,
            'total_premium': total_premium,
        })

class IndividualPoliciesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for individual users to access their own policies.
    """
    serializer_class = GroupEndowmentSerializer
    permission_classes = [IsAuthenticated, IsIndividualUser]
    
    def get_queryset(self):
        """
        Return only policies for the authenticated individual's group.
        """
        user = self.request.user
        individual = user.individual_profile
        
        # Get the individual's group ID
        group_id = individual.group_id.group_id if individual.group_id else None
        
        if not group_id:
            return GroupEndowment.objects.none()
        
        # Return policies for this individual (matching by employee_id or name)
        return GroupEndowment.objects.using('company_external').filter(
            group_id=group_id,
            employee_id=individual.user_id  # Adjust this field mapping as needed
        )

class GroupInformationFilter(django_filters.FilterSet):
    """
    Filter for GroupInformation view
    Only includes fields that exist in view_copo_groupInformation
    """
    group_id = django_filters.BaseInFilter(field_name='group_id', lookup_expr='in')

    class Meta:
        model = GroupInformation
        fields = {
            'is_active': ['exact'],
            'group_name': ['icontains'],  # Optional: search by group name
        }

@api_view(['GET'])  # Changed from POST to GET since we're not taking body params anymore
@permission_classes([IsAuthenticated])
@authentication_classes([JWTAuthentication, SessionAuthentication])
def group_information(request):
    """
    Get group information for the authenticated company's groups.
    GET /api/corporate/groups/
    
    Automatically fetches groups based on the logged-in company user.
    Superusers and staff can optionally pass company_id as query param.
    """

    
    user = request.user
    
    # Determine which company's groups to fetch
    if user.is_superuser or user.is_staff:
        # Staff/Superuser can optionally specify company_id
        company_id = request.query_params.get('company_id')
        
        if company_id:
            try:
                company_id = int(company_id)
                # Get group_ids for specified company
                group_ids = list(PortalGroup.objects.filter(
                    company_id=company_id,
                    isdeleted=False
                ).values_list('group_id', flat=True))
            except (ValueError, TypeError):
                log_report_access(
                    request=request,
                    report_type='Group Information',
                    sql_template='',
                    params=[],
                    status=ReportAccessLog.Status.INVALID_INPUT,
                )
                return Response({
                    'error': 'Invalid company_id'
                }, status=400)
        else:
            # If no company_id specified, return all groups (for superuser/staff)
            group_ids = list(PortalGroup.objects.filter(
                isdeleted=False
            ).values_list('group_id', flat=True))
    else:
        # Regular company user - get their own company's groups
        try:
            company = user.company_profile
            
            # Check if company account is active
            if not company.isactive:
                log_report_access(
                    request=request,
                    report_type='Group Information',
                    sql_template='',
                    params=[],
                    status=ReportAccessLog.Status.FORBIDDEN,
                )
                return Response({
                    'error': 'Company account is inactive'
                }, status=403)
            
            # Get all group_ids for this company from PostgreSQL
            group_ids = list(PortalGroup.objects.filter(
                company_id=company,
                isdeleted=False
            ).values_list('group_id', flat=True))
            
        except AttributeError:
                log_report_access(
                    request=request,
                    report_type='Group Information',
                    sql_template='',
                    params=[],
                    status=ReportAccessLog.Status.FORBIDDEN,
                )
                return Response({
                    'error': 'User is not associated with a company'
                }, status=403)
    
    # Check if company has any groups
    if not group_ids:
        log_report_access(
            request=request,
            report_type='Group Information',
            sql_template='',
            params=[],
            status=ReportAccessLog.Status.NO_DATA,
        )
        return Response({
            'count': 0,
            'results': [],
            'message': 'No groups found for this company'
        })
    
    # Fetch group information from MSSQL using the group_ids
    queryset = GroupInformation.objects.using('company_external').filter(
        group_id__in=group_ids
    )
    
    serializer = GroupInformationSerializer(queryset, many=True)
    
    log_report_access(
        request=request,
        report_type='Group Information',
        sql_template='',
        params=[],
        status=ReportAccessLog.Status.SUCCESS,
    )
    return Response({
        'count': queryset.count(),
        'group_ids': group_ids,  # Include for reference
        'results': serializer.data
    })

class GroupEndowmentViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API endpoint for Group Endowment from view_copo_groupEndowment.
    """
    queryset = GroupEndowment.objects.using('company_external').all()
    serializer_class = GroupEndowmentSerializer
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = [
        'group_id',
        'policy_status',
        'fiscal_year',
        'gender',
        'policy_type',
        'is_adb',
        'register_no',
        'employee_id',
        'claim_status',
    ]
    
    search_fields = [
        'name',
        'nep_name',
        'policy_no',
        'employee_id',
        'mobile',
        'email',
        'register_no',
    ]
    
    ordering_fields = [
        'maturity_date',
        'doc',
        'name',
        'premium',
        'sum_assured',
    ]
    
    ordering = ['-maturity_date']
    
    @action(detail=False, methods=['get'])
    def by_company(self, request):
        """
        Get all endowments for a specific company by company ID.
        Usage: /api/corporate/endowments/by_company/?company_id=1
        """
        from main_system.models import Group as PortalGroup
        
        company_id = request.query_params.get('company_id', None)
        
        if not company_id:
            return Response({
                'error': 'company_id parameter is required',
                'example': '/api/corporate/endowments/by_company/?company_id=1'
            }, status=400)
        
        # Validate company_id is a number
        try:
            company_id = int(company_id)
        except ValueError:
            return Response({
                'error': 'company_id must be a valid integer'
            }, status=400)
        
        # Get all group IDs for this company from portal database
        portal_groups = PortalGroup.objects.filter(
            company_id=company_id,
            isdeleted=False
        )
        
        group_ids = list(portal_groups.values_list('group_id', flat=True))
        
        if not group_ids:
            return Response({
                'company_id': company_id,
                'group_ids': [],
                'endowments': [],
                'count': 0,
                'message': 'No groups found for this company'
            })
        
        # Fetch endowments from external database view
        endowments = GroupEndowment.objects.using('company_external').filter(
            group_id__in=group_ids
        )
        
        # Serialize the data
        serializer = self.get_serializer(endowments, many=True)
        
        return Response({
            'company_id': company_id,
            'group_ids': group_ids,
            'count': endowments.count(),
            'endowments': serializer.data
        })