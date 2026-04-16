from django.urls import path, include #type: ignore
from rest_framework.routers import DefaultRouter #type: ignore
from rest_framework_simplejwt.views import TokenRefreshView #type: ignore
from .views import (
    policy_summary_report,
    CustomTokenObtainPairView,
    group_information,
    GroupEndowmentViewSet,
    CompanyPoliciesViewSet,
    IndividualPoliciesViewSet,
    loan_repayment_report,
    company_policies_web,
    maturity_forecasting_report,
    death_claim_report,
    maturity_claim_report,
    surrender_claim_report,
    policy_search,
    policy_loans,
    group_transfer_report,
    group_business_detail_report,
    surrender_calculator,
)

router = DefaultRouter()
router.register(r'company/policies', CompanyPoliciesViewSet, basename='company-policies')
router.register(r'endowments', GroupEndowmentViewSet, basename='endowment')
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
    path('reports/loan-repayment/', loan_repayment_report, name='loan-repayment-report'),
    #Policy Summary
    path('policy-search/', policy_search, name='policy-search'),
    path('reports/policy-loans/', policy_loans, name='policy-loans'),
    path('surrender-calculator/', surrender_calculator, name='surrender-calculator'),
    path('policy-summary/', policy_summary_report, name='policy-summary-report'),
    #CLaim Reports
    path('reports/maturity-claim/', maturity_claim_report, name='maturity-claim-report'),
    path('reports/death-claim/', death_claim_report, name='death-claim-report'),
    path('reports/surrender-claim/', surrender_claim_report, name='surrender-claim-report'),

    #Transfer Report
    path('reports/group-transfer/', group_transfer_report, name='group-transfer-report'),

    #Group Business Report
    path('reports/group-business-detail/', group_business_detail_report, name='group-business-detail-report'),
    # API endpoints
    path('', include(router.urls)),
]