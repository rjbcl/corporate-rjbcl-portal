from rest_framework import viewsets, filters #type: ignore
from rest_framework.permissions import IsAuthenticated #type: ignore
from rest_framework.decorators import action #type: ignore
from rest_framework.response import Response #type: ignore
from django_filters.rest_framework import DjangoFilterBackend #type: ignore
from .models import GroupEndowment, GroupInformation
from .serializers import GroupEndowmentSerializer, GroupInformationSerializer


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