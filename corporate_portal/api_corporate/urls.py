from django.urls import path, include #type: ignore
from rest_framework.routers import DefaultRouter #type: ignore
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView,
    GroupInformationViewSet,
    GroupEndowmentViewSet,
    CompanyPoliciesViewSet,
    IndividualPoliciesViewSet,
    company_policies_web
)

router = DefaultRouter()
router.register(r'groups', GroupInformationViewSet, basename='group')
router.register(r'endowments', GroupEndowmentViewSet, basename='endowment')
router.register(r'company/policies', CompanyPoliciesViewSet, basename='company-policies')
router.register(r'individual/policies', IndividualPoliciesViewSet, basename='individual-policies')

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),


    # Web dashboard endpoint (Session auth)
    path('endowments/by_company/', company_policies_web, name='company-policies-web'),
    
    # API endpoints
    path('', include(router.urls)),
]