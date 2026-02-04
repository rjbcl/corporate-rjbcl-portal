from django.urls import path, include #type: ignore
from rest_framework.routers import DefaultRouter #type: ignore
from rest_framework_simplejwt.views import TokenRefreshView #type: ignore
from .views import (
    CustomTokenObtainPairView,
    group_information,
    GroupEndowmentViewSet,
    CompanyPoliciesViewSet,
    IndividualPoliciesViewSet,
    company_policies_web,
    maturity_forecasting_report,
    death_claim_report,
    maturity_claim_report,
    surrender_claim_report
)

router = DefaultRouter()
router.register(r'endowments', GroupEndowmentViewSet, basename='endowment')
router.register(r'company/policies', CompanyPoliciesViewSet, basename='company-policies')
router.register(r'individual/policies', IndividualPoliciesViewSet, basename='individual-policies')

urlpatterns = [
    # Authentication endpoints
    path('auth/login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    #Group Information
    path('groups/', group_information, name='group-information'),

    # Web dashboard endpoint (Session auth)
    path('endowments/by_company/', company_policies_web, name='company-policies-web'),

    # Reports endpoint
    path('reports/maturity-forecasting/', maturity_forecasting_report, name='maturity-forecasting'),
    path('reports/maturity-claim/', maturity_claim_report, name='maturity-claim-report'),
    path('reports/death-claim/', death_claim_report, name='death-claim-report'),
    path('reports/surrender-claim/', surrender_claim_report, name='surrender-claim-report'),
    
    # API endpoints
    path('', include(router.urls)),
]