from rest_framework import viewsets, filters, status, serializers  #type: ignore
from rest_framework.permissions import IsAuthenticated #type: ignore
from rest_framework.decorators import action #type: ignore
from rest_framework.response import Response #type: ignore
from django_filters.rest_framework import DjangoFilterBackend #type: ignore
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.decorators import api_view, permission_classes
from .models import GroupEndowment, GroupInformation
from .serializers import (
    GroupEndowmentSerializer, 
    GroupInformationSerializer,
    CustomTokenObtainPairSerializer
)
from .permissions import IsCompanyUser, IsIndividualUser

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
        return Response(serializer.validated_data, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def company_policies_web(request):
    """
    Web dashboard endpoint - uses Django session authentication.
    GET /api/corporate/endowments/by_company/?company_id=<id>
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
    
    # Security: Verify the logged-in user owns this company
    if not request.user.is_superuser and not request.user.is_staff:
        user_company_id = request.user.company_profile.company_id
        if user_company_id != company_id:
            return Response({
                'error': 'You can only access your own company data'
            }, status=403)
    
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
    serializer = GroupEndowmentSerializer(endowments, many=True)
    
    return Response({
        'company_id': company_id,
        'group_ids': group_ids,
        'count': endowments.count(),
        'endowments': serializer.data
    })

class CompanyPoliciesViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for company users to access their policies.
    Automatically filters by authenticated company.
    """
    serializer_class = GroupEndowmentSerializer
    permission_classes = [IsAuthenticated, IsCompanyUser]
    
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
        from main_system.models import Group as PortalGroup
        
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
    
    @action(detail=False, methods=['get'])
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

class GroupInformationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API endpoint for Group Information.
    
    Provides list and retrieve actions only (GET requests).
    Supports filtering, searching, and ordering.
    """
    queryset = GroupInformation.objects.using('company_external').all()
    serializer_class = GroupInformationSerializer
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    filterset_fields = [
        'group_id',
        'fiscal_year',
        'is_active',
        'group_type',
        'account_number',
    ]
    
    search_fields = [
        'group_name',
        'group_name_nepali',
        'short_name',
        'master_policy_no',
        'group_id',
    ]
    
    ordering_fields = [
        'created_date',
        'modified_date',
        'group_name',
        'fiscal_year',
    ]
    
    ordering = ['-created_date']

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