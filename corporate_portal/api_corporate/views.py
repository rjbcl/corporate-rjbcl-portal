from rest_framework import viewsets, filters #type: ignore
from rest_framework.permissions import IsAuthenticated #type: ignore
from django_filters.rest_framework import DjangoFilterBackend #type: ignore
from .models import GroupInformation
from .serializers import GroupInformationSerializer


class GroupInformationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API endpoint for Group Information.
    
    Provides list and retrieve actions only (GET requests).
    Supports filtering, searching, and ordering.
    """
    queryset = GroupInformation.objects.using('company_external').all()
    serializer_class = GroupInformationSerializer

    permission_classes = [IsAuthenticated]
    
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