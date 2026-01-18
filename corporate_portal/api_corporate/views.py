from rest_framework import viewsets, filters #type: ignore
from rest_framework.permissions import IsAuthenticated #type: ignore
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
    Read-only API endpoint for Group Endowment (Individual Policies).
    
    Provides list and retrieve actions only (GET requests).
    Supports filtering, searching, and ordering.
    """
    queryset = GroupEndowment.objects.using('company_external').all()
    serializer_class = GroupEndowmentSerializer
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    
    # Fields that can be filtered exactly
    filterset_fields = [
        'group_id',
        'policy_status',
        'fiscal_year',
        'gender',
        'policy_type',
        'branch',
        'is_adb',
        'register_no',
        'employee_id',
    ]
    
    # Fields that can be searched (partial match)
    search_fields = [
        'name',
        'nep_name',
        'policy_no',
        'employee_id',
        'mobile',
        'email',
        'register_no',
    ]
    
    # Fields that can be used for ordering
    ordering_fields = [
        'created_date',
        'modified_date',
        'name',
        'doc',
        'maturity_date',
        'premium',
    ]
    
    ordering = ['-created_date']
